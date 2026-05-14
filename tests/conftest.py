"""
Fixtures partagées pour les tests.

Les modèles sont chargés depuis le MLflow Model Registry.
Prérequis : MLflow tourne sur l'URI configurée dans config/config.yaml
et les modèles sont en stage "Production".

    mlflow server --backend-store-uri sqlite:///mlruns.db --host 0.0.0.0 --port 5000 or mlflow ui
    python -m src.models.train_stage1
    python -m src.models.train_stage2
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def predictor():
    """Instance de MaintenancePredictor chargée depuis le MLflow Model Registry."""
    try:
        from src.pipeline.predictor import MaintenancePredictor
        return MaintenancePredictor.from_mlflow()
    except Exception as exc:
        pytest.skip(f"MLflow Registry indisponible : {exc}")


@pytest.fixture(scope="session")
def api_client(predictor):
    """Client HTTP TestClient FastAPI avec modèles pré-chargés depuis MLflow."""
    from fastapi.testclient import TestClient
    import api.routers.predict as predict_module
    predict_module._predictor = predictor
    from api.main import app
    return TestClient(app)


@pytest.fixture
def normal_reading() -> dict:
    return {
        "product_type": "M",
        "air_temperature_k": 298.5,
        "process_temperature_k": 308.5,
        "rotational_speed_rpm": 1500,
        "torque_nm": 35.0,
        "tool_wear_min": 50,
    }


@pytest.fixture
def critical_reading() -> dict:
    """Scénario OSF : usure élevée + couple fort → surcontrainte attendue."""
    return {
        "product_type": "L",
        "air_temperature_k": 303.0,
        "process_temperature_k": 311.0,
        "rotational_speed_rpm": 1350,
        "torque_nm": 68.0,
        "tool_wear_min": 200,
    }
