"""Tests de l'API FastAPI et du predictor."""
from __future__ import annotations


# ── /health ───────────────────────────────────────────────────────────────

def test_health(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["models_loaded"] is True
    assert isinstance(body["threshold"], float)


# ── /predict — machine normale ────────────────────────────────────────────

def test_predict_normal_machine(api_client, normal_reading):
    resp = api_client.post("/predict", json=normal_reading)
    assert resp.status_code == 200
    body = resp.json()
    assert "failure_proba" in body
    assert "failure_alert" in body
    assert isinstance(body["failure_alert"], bool)
    assert body["failure_alert"] is False, "Machine normale ne doit pas déclencher d'alerte"


# ── /predict — scénario critique ──────────────────────────────────────────

def test_predict_critical_machine(api_client, critical_reading):
    resp = api_client.post("/predict", json=critical_reading)
    assert resp.status_code == 200
    body = resp.json()
    assert body["failure_alert"] is True, "Scénario critique doit déclencher une alerte"
    assert len(body["failure_types"]) > 0
    assert len(body["recommended_actions"]) > 0


# ── Validation des entrées ────────────────────────────────────────────────

def test_predict_invalid_type(api_client, normal_reading):
    """Type de produit invalide → 422 Unprocessable Entity."""
    payload = {**normal_reading, "product_type": "Z"}
    resp = api_client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_predict_process_temp_below_air(api_client, normal_reading):
    """T_process <= T_air → 422 (validation physique)."""
    payload = {**normal_reading, "process_temperature_k": 295.0, "air_temperature_k": 300.0}
    resp = api_client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_predict_missing_field(api_client):
    """Champ obligatoire manquant → 422."""
    resp = api_client.post("/predict", json={"Type": "M"})
    assert resp.status_code == 422


# ── Predictor unitaire ────────────────────────────────────────────────────

def test_predictor_output_schema(predictor, normal_reading):
    result = predictor.predict_from_sensors(normal_reading)
    assert set(result.keys()) == {
        "failure_proba", "failure_alert", "failure_types", "recommended_actions"
    }
    assert 0.0 <= result["failure_proba"] <= 1.0
    assert isinstance(result["failure_types"], list)
    assert isinstance(result["recommended_actions"], list)


def test_predictor_feature_engineering(predictor):
    """Vérifie que predict_from_sensors accepte les noms de colonnes du dataset."""
    reading = {
        "Type": "H",
        "Air temperature [K]": 301.0,
        "Process temperature [K]": 311.0,
        "Rotational speed [rpm]":  1600,
        "Torque [Nm]": 30.0,
        "Tool wear [min]": 10,
    }
    result = predictor.predict_from_sensors(reading)
    assert result["failure_proba"] >= 0
