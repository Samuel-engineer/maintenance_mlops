"""
Entraînement du Stage 1 (détection binaire) avec tracking MLflow.

Usage :
    python -m src.models.train_stage1
"""
from __future__ import annotations

import pathlib
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
import yaml
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    recall_score, precision_score, fbeta_score, classification_report,
)
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from src.data.loader import load_raw
from src.data.features import build_feature_matrix


CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config" / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def find_optimal_threshold(proba: np.ndarray, y_true: np.ndarray, beta: float = 2) -> float:
    """Retourne le seuil qui maximise le F-beta score."""
    thresholds = np.linspace(0.01, 0.99, 300)
    scores = [
        fbeta_score(y_true, (proba >= t).astype(int), beta=beta, zero_division=0)
        for t in thresholds
    ]
    return float(thresholds[int(np.argmax(scores))])


def train(cfg: dict | None = None) -> tuple:
    """
    Entraîne le pipeline Stage 1, log dans MLflow et retourne
    (pipeline, threshold, run_id).
    """
    if cfg is None:
        cfg = load_config()
    import os  
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")


    dcfg  = cfg["data"]
    s1cfg = cfg["stage1"]
    mlcfg = cfg["mlflow"]
    features = cfg["features"]["raw"] + cfg["features"]["engineered"]

    # ── Données ──────────────────────────────────────────────────────────
    df_raw = load_raw(dcfg["kaggle_dataset"], dcfg["kaggle_file"], dcfg["index_col"])
    X = build_feature_matrix(df_raw, features)
    y = df_raw["Machine failure"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=dcfg["test_size"],
        random_state=dcfg["random_state"],
        stratify=y,
    )

    # ── Pipeline ─────────────────────────────────────────────────────────
    pipeline = ImbPipeline([
        ("scaler", StandardScaler()),
        ("smote",  SMOTE(random_state=s1cfg["smote"]["random_state"])),
        ("clf",    GradientBoostingClassifier(**s1cfg["params"])),
    ])

    # ── MLflow run ───────────────────────────────────────────────────────
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(mlcfg["experiment_name"])

    with mlflow.start_run(run_name="stage1_training") as run:
        # Log hyperparamètres
        mlflow.log_params(s1cfg["params"])
        mlflow.log_param("smote_random_state", s1cfg["smote"]["random_state"])
        mlflow.log_param("test_size", dcfg["test_size"])
        mlflow.log_param("n_features", len(features))

        # Validation croisée
        cv = StratifiedKFold(n_splits=s1cfg["cv_folds"], shuffle=True, random_state=dcfg["random_state"])
        cv_auc = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="roc_auc")
        cv_ap  = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="average_precision")
        mlflow.log_metric("cv_roc_auc_mean",  float(cv_auc.mean()))
        mlflow.log_metric("cv_roc_auc_std",   float(cv_auc.std()))
        mlflow.log_metric("cv_avg_precision_mean", float(cv_ap.mean()))

        # Entraînement final
        pipeline.fit(X_train, y_train)
        y_proba = pipeline.predict_proba(X_test)[:, 1]

        # Seuil optimal
        threshold = find_optimal_threshold(y_proba, y_test, beta=s1cfg["threshold_beta"])
        y_pred = (y_proba >= threshold).astype(int)

        # Métriques test
        test_auc    = roc_auc_score(y_test, y_proba)
        test_ap     = average_precision_score(y_test, y_proba)
        test_recall = recall_score(y_test, y_pred, zero_division=0)
        test_prec   = precision_score(y_test, y_pred, zero_division=0)
        test_f2     = fbeta_score(y_test, y_pred, beta=2, zero_division=0)

        mlflow.log_metric("test_roc_auc",   test_auc)
        mlflow.log_metric("test_avg_prec",  test_ap)
        mlflow.log_metric("test_recall",    test_recall)
        mlflow.log_metric("test_precision", test_prec)
        mlflow.log_metric("test_f2",        test_f2)
        mlflow.log_metric("threshold",      threshold)

        # Log du rapport texte comme artefact
        report = classification_report(y_test, y_pred,
                                       target_names=["Normal", "Failure"])
        mlflow.log_text(report, "classification_report_stage1.txt")

        # Log du modèle scikit-learn
        mlflow.sklearn.log_model(
            sk_model=pipeline,
            name="stage1_pipeline",
            registered_model_name=mlcfg["registered_model_stage1"],
            input_example=X_test.iloc[:3],
        )

        # Assigne l'alias champion à la version fraîchement enregistrée
        _client = mlflow.MlflowClient()
        _versions = _client.search_model_versions(
            f"name='{mlcfg['registered_model_stage1']}' and run_id='{run.info.run_id}'"
        )
        if _versions:
            _client.set_registered_model_alias(
                mlcfg["registered_model_stage1"], "champion", _versions[0].version
            )
            print(f"  alias 'champion' → v{_versions[0].version}")

        # # Sauvegarde locale en supplément
        # artifacts_dir = pathlib.Path(cfg["artifacts"]["models_dir"])
        # # artifacts_dir.mkdir(parents=True, exist_ok=True)
        # # import joblib
        # # joblib.dump(pipeline,  artifacts_dir / "stage1_pipeline.pkl")
        # # joblib.dump(threshold, artifacts_dir / "stage1_threshold.pkl")

        # mlflow.log_artifact(str(artifacts_dir / "stage1_pipeline.pkl"))

        run_id = run.info.run_id
        print(f"[Stage 1] run_id={run_id}")
        print(f"  ROC-AUC  : {test_auc:.4f}")
        print(f"  Recall   : {test_recall:.4f}  (seuil={threshold:.3f})")
        print(f"  F2       : {test_f2:.4f}")

    return pipeline, threshold, run_id


if __name__ == "__main__":
    train()
