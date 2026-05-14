"""Router FastAPI — endpoint /predict."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from api.schemas import SensorReading, PredictionResponse
from src.pipeline.predictor import MaintenancePredictor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["prediction"])

_predictor: MaintenancePredictor | None = None


def load_predictor() -> None:
    """
    Initialise le predictor depuis MLflow (prioritaire) ou les artefacts locaux
    en fallback si MLflow est indisponible.
    """
    global _predictor
    try:
        _predictor = MaintenancePredictor.from_mlflow()
        logger.info("Modèles chargés depuis MLflow Model Registry")
    except Exception as mlflow_exc:
        logger.warning(
            "MLflow indisponible (%s) — tentative de chargement local", mlflow_exc
        )
        try:
            _predictor = MaintenancePredictor.from_local()
            logger.info("Modèles chargés depuis les artefacts locaux (fallback)")
        except Exception as local_exc:
            logger.error("Échec du chargement local : %s", local_exc)
            raise RuntimeError(
                f"Impossible de charger les modèles (MLflow: {mlflow_exc} | local: {local_exc})"
            ) from local_exc


def get_predictor() -> MaintenancePredictor:
    if _predictor is None:
        raise HTTPException(status_code=503, detail="Modèles non chargés — relancer après entraînement")
    return _predictor


def get_model_info() -> dict:
    """Retourne les métadonnées de chargement des modèles (utilisé par /health)."""
    return {
        "models_loaded": _predictor is not None,
        "threshold": round(_predictor.threshold, 4) if _predictor else None,
    }


# ── Endpoint ──────────────────────────────────────────────────────────────

@router.post("", response_model=PredictionResponse, status_code=200)
def predict(reading: SensorReading) -> PredictionResponse:
    """
    Reçoit une ligne de mesures capteurs et retourne :
    - `failure_proba` : probabilité de panne (Stage 1)
    - `failure_alert` : `true` si la probabilité dépasse le seuil optimisé
    - `failure_types` : type(s) de pannes détectés (Stage 2, vide si pas d'alerte)
    - `recommended_actions` : actions de maintenance associées
    """
    predictor = get_predictor()
    logger.info(
        "Prédiction demandée — type=%s rpm=%d torque=%.1f wear=%d",
        reading.product_type,
        reading.rotational_speed_rpm,
        reading.torque_nm,
        reading.tool_wear_min,
    )
    result = predictor.predict_from_sensors(reading.to_raw_dict())
    logger.info(
        "Résultat — alerte=%s proba=%.3f types=%s",
        result["failure_alert"],
        result["failure_proba"],
        result["failure_types"],
    )
    return PredictionResponse(**result)
