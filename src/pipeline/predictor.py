"""
MaintenancePredictor : orchestre Stage 1 + Stage 2.

Peut être chargé depuis des artefacts locaux (joblib) ou depuis le
Model Registry MLflow.
"""
from __future__ import annotations

import pathlib
import numpy as np
import pandas as pd
import yaml

from src.data.features import engineer_features

CONFIG_PATH = pathlib.Path(__file__).parents[2] / "config" / "config.yaml"

FAILURE_ACTIONS: dict[str, str] = {
    "TWF": "Remplacer l'outil immédiatement (Tool Wear Failure)",
    "HDF": "Vérifier le système de refroidissement — écart T trop faible (Heat Dissipation)",
    "PWF": "Ajuster vitesse/couple — puissance hors plage [3 500 W – 9 000 W] (Power Failure)",
    "OSF": "Réduire la charge — produit usure×couple dépasse le seuil type (Overstrain)",
    "RNF": "Inspection générale requise — panne aléatoire non attribuable",
}


class MaintenancePredictor:
    """
    Pipeline de maintenance prédictive en deux étapes.

    Paramètres
    ----------
    stage1_pipeline : ImbPipeline  (Scaler + SMOTE + GBM)
    stage2_pipeline : Pipeline     (Scaler + MultiOutputClassifier RF)
    threshold       : float        seuil de décision Stage 1
    features        : list[str]    noms des features (ordre identique à l'entraînement)
    failure_types   : list[str]    noms des types de pannes Stage 2
    """

    def __init__(
        self,
        stage1_pipeline,
        stage2_pipeline,
        threshold: float,
        features: list[str] | None = None,
        failure_types: list[str] | None = None,
    ) -> None:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        self.s1_pipe       = stage1_pipeline
        self.s2_pipe       = stage2_pipeline
        self.threshold     = threshold
        self.features      = features or (cfg["features"]["raw"] + cfg["features"]["engineered"])
        self.failure_types = failure_types or cfg["data"]["failure_types"]

    # ── Chargement depuis artefacts locaux ────────────────────────────────
    @classmethod
    def from_local(cls, models_dir: str | pathlib.Path | None = None) -> "MaintenancePredictor":
        import joblib
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        models_dir = pathlib.Path(models_dir or cfg["artifacts"]["models_dir"])
        s1 = joblib.load(models_dir / "stage1_pipeline.pkl")
        s2 = joblib.load(models_dir / "stage2_pipeline.pkl")
        threshold = joblib.load(models_dir / "stage1_threshold.pkl")
        return cls(s1, s2, threshold)

    # ── Chargement depuis MLflow Model Registry ───────────────────────────
    @classmethod
    def from_mlflow(cls, alias: str | None = None) -> "MaintenancePredictor":
        """Charge les modèles enregistrés dans le MLflow Model Registry via alias."""
        import os
        import mlflow
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        mlcfg = cfg["mlflow"]
        # URI et alias viennent exclusivement des variables d'environnement
        tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
        _alias = alias or os.environ.get("MODEL_ALIAS", "champion")
        mlflow.set_tracking_uri(tracking_uri)
        s1_name = mlcfg["registered_model_stage1"]
        s2_name = mlcfg["registered_model_stage2"]
        s1 = mlflow.sklearn.load_model(f"models:/{s1_name}@{_alias}")
        s2 = mlflow.sklearn.load_model(f"models:/{s2_name}@{_alias}")
        # Récupère le seuil depuis les métriques du run associé au modèle
        client = mlflow.MlflowClient()
        version = client.get_model_version_by_alias(s1_name, _alias)
        run_data = client.get_run(version.run_id).data
        threshold = float(run_data.metrics["threshold"])
        return cls(s1, s2, threshold)

    # ── Prédiction sur DataFrame déjà engineeré ───────────────────────────
    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Entrée  : X avec les features déjà calculées (9 colonnes).
        Sortie  : DataFrame avec failure_proba, failure_alert, failure_types.
        """
        res = pd.DataFrame(index=X.index)
        proba = self.s1_pipe.predict_proba(X)[:, 1]
        res["failure_proba"] = proba.round(4)
        res["failure_alert"] = proba >= self.threshold
        res["failure_types"] = [[] for _ in range(len(X))]

        alert_idx = res[res["failure_alert"]].index
        if len(alert_idx) > 0:
            preds = self.s2_pipe.predict(X.loc[alert_idx])
            for i, idx in enumerate(alert_idx):
                detected = [
                    ft for j, ft in enumerate(self.failure_types) if preds[i, j] == 1
                ]
                res.at[idx, "failure_types"] = detected or ["Indéterminé"]

        return res

    # Mapping clés API snake_case → noms de colonnes AI4I originaux
    _SENSOR_KEY_MAP = {
        "product_type":          "Type",
        "air_temperature_k":     "Air temperature [K]",
        "process_temperature_k": "Process temperature [K]",
        "rotational_speed_rpm":  "Rotational speed [rpm]",
        "torque_nm":             "Torque [Nm]",
        "tool_wear_min":         "Tool wear [min]",
    }

    # ── Prédiction à partir de données brutes capteurs ────────────────────
    def predict_from_sensors(self, raw: dict) -> dict:
        """
        Entrée  : dict de mesures brutes — accepte clés snake_case (API) ou noms AI4I.
        Sortie  : dict structuré avec proba, alerte, types et actions recommandées.
        """
        normalized = {self._SENSOR_KEY_MAP.get(k, k): v for k, v in raw.items()}
        df_raw = pd.DataFrame([normalized])
        df_eng = engineer_features(df_raw)
        result = self.predict(df_eng[self.features]).iloc[0]

        failure_types = result["failure_types"]
        actions = (
            [FAILURE_ACTIONS.get(ft, ft) for ft in failure_types]
            if failure_types
            else []
        )

        return {
            "failure_proba":       float(result["failure_proba"]),
            "failure_alert":       bool(result["failure_alert"]),
            "failure_types":       failure_types,
            "recommended_actions": actions or ["Aucune action requise"],
        }
