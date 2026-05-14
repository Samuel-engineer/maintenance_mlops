"""
Entraînement du Stage 2 (diagnostic multi-label) avec tracking MLflow.

Usage :
    python -m src.models.train_stage2
"""
from __future__ import annotations

import pathlib
import numpy as np
import mlflow
import mlflow.sklearn
import yaml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, roc_auc_score

from src.data.loader import load_raw
from src.data.features import build_feature_matrix

CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config" / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def train(cfg: dict | None = None) -> tuple:
    """
    Entraîne le pipeline Stage 2 sur les observations failure=1 uniquement,
    log dans MLflow et retourne (pipeline, run_id).
    """
    if cfg is None:
        cfg = load_config()
    import os  
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")

    dcfg     = cfg["data"]
    s2cfg    = cfg["stage2"]
    mlcfg    = cfg["mlflow"]
    features = cfg["features"]["raw"] + cfg["features"]["engineered"]
    failure_types = dcfg["failure_types"]

    # ── Données ──────────────────────────────────────────────────────────
    df_raw = load_raw(dcfg["kaggle_dataset"], dcfg["kaggle_file"], dcfg["index_col"])
    X = build_feature_matrix(df_raw, features)
    y_stage1 = df_raw["Machine failure"]
    y_stage2 = df_raw[failure_types]

    X_train, X_test, y1_train, y1_test, y2_train, y2_test = train_test_split(
        X, y_stage1, y_stage2,
        test_size=dcfg["test_size"],
        random_state=dcfg["random_state"],
        stratify=y_stage1,
    )

    # Filtrage sur failure = 1 uniquement
    X2_train  = X_train[y1_train == 1]
    y2_train_f = y2_train[y1_train == 1]
    X2_test   = X_test[y1_test == 1]
    y2_test_f  = y2_test[y1_test == 1]

    # ── Pipeline ─────────────────────────────────────────────────────────
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    MultiOutputClassifier(
            RandomForestClassifier(**s2cfg["params"])
        )),
    ])

    # ── MLflow run ───────────────────────────────────────────────────────
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(mlcfg["experiment_name"])

    with mlflow.start_run(run_name="stage2_training") as run:
        mlflow.log_params(s2cfg["params"])
        mlflow.log_param("train_size_stage2", len(X2_train))
        mlflow.log_param("test_size_stage2",  len(X2_test))

        pipeline.fit(X2_train, y2_train_f)
        y2_pred = pipeline.predict(X2_test)

        # Probas correctement scalées
        X2_test_scaled = pipeline.named_steps["scaler"].transform(X2_test)
        y2_proba = np.column_stack([
            est.predict_proba(X2_test_scaled)[:, 1]
            for est in pipeline.named_steps["clf"].estimators_
        ])

        # Métriques par type de panne
        for i, ft in enumerate(failure_types):
            n_pos = int(y2_test_f[ft].sum())
            if n_pos >= 2:
                auc = roc_auc_score(y2_test_f[ft], y2_proba[:, i])
                mlflow.log_metric(f"test_roc_auc_{ft}", auc)

        report = classification_report(y2_test_f, y2_pred,
                                       target_names=failure_types,
                                       zero_division=0)
        mlflow.log_text(report, "classification_report_stage2.txt")

        mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="stage2_pipeline",
            registered_model_name=mlcfg["registered_model_stage2"],
            input_example=X2_test.iloc[:3],
        )

        # Assigne l'alias champion à la version fraîchement enregistrée
        _client = mlflow.MlflowClient()
        _versions = _client.search_model_versions(
            f"name='{mlcfg['registered_model_stage2']}' and run_id='{run.info.run_id}'"
        )
        if _versions:
            _client.set_registered_model_alias(
                mlcfg["registered_model_stage2"], "champion", _versions[0].version
            )
            print(f"alias 'champion' → v{_versions[0].version}")

        # artifacts_dir = pathlib.Path(cfg["artifacts"]["models_dir"])
        # # artifacts_dir.mkdir(parents=True, exist_ok=True)
        # # import joblib
        # # joblib.dump(pipeline, artifacts_dir / "stage2_pipeline.pkl")
        # mlflow.log_artifact(str(artifacts_dir / "stage2_pipeline.pkl"))

        run_id = run.info.run_id
        print(f"[Stage 2] run_id={run_id}")
        print(report)

    return pipeline, run_id


if __name__ == "__main__":
    train()
