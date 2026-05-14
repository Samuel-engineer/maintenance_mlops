"""Tests pour src/models/train_stage1.py et train_stage2.py."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_raw_df(n: int = 200) -> pd.DataFrame:
    """DataFrame synthétique qui imite le format AI4I brut (suffisamment grand
    pour que SMOTE et le split train/test fonctionnent)."""
    rng = np.random.default_rng(42)
    failure = rng.integers(0, 2, n)
    df = pd.DataFrame(
        {
            "Type":                        rng.choice(["L", "M", "H"], n),
            "Air temperature [K]":         rng.uniform(295, 305, n),
            "Process temperature [K]":     rng.uniform(306, 315, n),
            "Rotational speed [rpm]":      rng.integers(1200, 2900, n).astype(float),
            "Torque [Nm]":                 rng.uniform(10, 80, n),
            "Tool wear [min]":             rng.integers(0, 250, n).astype(float),
            "Machine failure":             failure,
            "TWF":                         np.where(failure, rng.integers(0, 2, n), 0),
            "HDF":                         np.where(failure, rng.integers(0, 2, n), 0),
            "PWF":                         np.where(failure, rng.integers(0, 2, n), 0),
            "OSF":                         np.where(failure, rng.integers(0, 2, n), 0),
            "RNF":                         np.where(failure, rng.integers(0, 2, n), 0),
        },
        index=pd.RangeIndex(1, n + 1, name="UDI"),
    )
    return df


@contextmanager
def _patch_mlflow():
    """Remplace mlflow par un mock pour éviter toute connexion réseau."""
    mock_run = MagicMock()
    mock_run.__enter__ = lambda s: s
    mock_run.__exit__ = MagicMock(return_value=False)
    mock_run.info.run_id = "fake-run-id"

    with patch("mlflow.set_tracking_uri"), \
         patch("mlflow.set_experiment"), \
         patch("mlflow.start_run", return_value=mock_run), \
         patch("mlflow.log_params"), \
         patch("mlflow.log_param"), \
         patch("mlflow.log_metric"), \
         patch("mlflow.log_text"), \
         patch("mlflow.sklearn.log_model"):
        yield


# ── find_optimal_threshold ───────────────────────────────────────────────────

class TestFindOptimalThreshold:
    def test_returns_float(self):
        from src.models.train_stage1 import find_optimal_threshold
        rng = np.random.default_rng(0)
        proba = rng.uniform(0, 1, 100)
        y = (proba > 0.5).astype(int)
        t = find_optimal_threshold(proba, y)
        assert isinstance(t, float)

    def test_threshold_in_unit_interval(self):
        from src.models.train_stage1 import find_optimal_threshold
        rng = np.random.default_rng(1)
        proba = rng.uniform(0, 1, 100)
        y = (proba > 0.4).astype(int)
        t = find_optimal_threshold(proba, y)
        assert 0.0 <= t <= 1.0

    def test_threshold_separates_classes(self):
        """Avec des probas propres le seuil doit être proche de 0.5."""
        from src.models.train_stage1 import find_optimal_threshold
        proba = np.concatenate([np.linspace(0.0, 0.45, 50), np.linspace(0.55, 1.0, 50)])
        y = np.array([0] * 50 + [1] * 50)
        t = find_optimal_threshold(proba, y)
        assert t < 0.7, f"Seuil inattendu : {t}"


# ── train_stage1 ─────────────────────────────────────────────────────────────

class TestTrainStage1:
    @pytest.fixture(autouse=True)
    def _mock_deps(self):
        raw = _make_raw_df(300)
        with patch("src.models.train_stage1.load_raw", return_value=raw), \
             _patch_mlflow():
            yield

    def test_returns_three_elements(self):
        from src.models.train_stage1 import train
        result = train()
        assert len(result) == 3

    def test_pipeline_has_predict_proba(self):
        from src.models.train_stage1 import train
        pipeline, _, _ = train()
        assert hasattr(pipeline, "predict_proba")

    def test_threshold_is_float_in_range(self):
        from src.models.train_stage1 import train
        _, threshold, _ = train()
        assert isinstance(threshold, float)
        assert 0.0 <= threshold <= 1.0

    def test_run_id_is_string(self):
        from src.models.train_stage1 import train
        _, _, run_id = train()
        assert isinstance(run_id, str)

    def test_pipeline_predict_shape(self):
        from src.models.train_stage1 import train
        from src.data.features import build_feature_matrix
        import yaml, pathlib
        cfg = yaml.safe_load((pathlib.Path(__file__).parents[1] / "config" / "config.yaml").read_text())
        features = cfg["features"]["raw"] + cfg["features"]["engineered"]
        raw = _make_raw_df(50)
        X = build_feature_matrix(raw, features)
        pipeline, _, _ = train()
        preds = pipeline.predict_proba(X)
        assert preds.shape == (len(X), 2)


# ── train_stage2 ─────────────────────────────────────────────────────────────

class TestTrainStage2:
    @pytest.fixture(autouse=True)
    def _mock_deps(self):
        raw = _make_raw_df(300)
        with patch("src.models.train_stage2.load_raw", return_value=raw), \
             _patch_mlflow():
            yield

    def test_returns_two_elements(self):
        from src.models.train_stage2 import train
        result = train()
        assert len(result) == 2

    def test_pipeline_has_predict(self):
        from src.models.train_stage2 import train
        pipeline, _ = train()
        assert hasattr(pipeline, "predict")

    def test_run_id_is_string(self):
        from src.models.train_stage2 import train
        _, run_id = train()
        assert isinstance(run_id, str)

    def test_pipeline_predict_shape(self):
        from src.models.train_stage2 import train
        from src.data.features import build_feature_matrix
        import yaml, pathlib
        cfg = yaml.safe_load((pathlib.Path(__file__).parents[1] / "config" / "config.yaml").read_text())
        features = cfg["features"]["raw"] + cfg["features"]["engineered"]
        failure_types = cfg["data"]["failure_types"]
        raw = _make_raw_df(50)
        # Stage 2 prédit uniquement sur les lignes failure=1
        X_fail = build_feature_matrix(raw[raw["Machine failure"] == 1], features)
        if X_fail.empty:
            pytest.skip("Pas de failure dans le dataset synthétique")
        pipeline, _ = train()
        preds = pipeline.predict(X_fail)
        assert preds.shape[1] == len(failure_types)
