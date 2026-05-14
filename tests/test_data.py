"""Tests pour src/data/loader.py et src/data/features.py."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from src.data.features import engineer_features, build_feature_matrix


# ── Données synthétiques réutilisables ───────────────────────────────────────

def _make_raw_df(n: int = 10) -> pd.DataFrame:
    """DataFrame synthétique qui imite le format AI4I brut."""
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "Type":                        rng.choice(["L", "M", "H"], n),
            "Air temperature [K]":         rng.uniform(295, 305, n),
            "Process temperature [K]":     rng.uniform(306, 315, n),
            "Rotational speed [rpm]":      rng.integers(1200, 2900, n).astype(float),
            "Torque [Nm]":                 rng.uniform(10, 80, n),
            "Tool wear [min]":             rng.integers(0, 250, n).astype(float),
            "Machine failure":             rng.integers(0, 2, n),
        }
    )


# ── engineer_features ────────────────────────────────────────────────────────

class TestEngineerFeatures:
    def setup_method(self):
        self.df = _make_raw_df(20)
        self.out = engineer_features(self.df)

    def test_adds_power_w(self):
        assert "power_W" in self.out.columns

    def test_power_w_formula(self):
        expected = self.df["Torque [Nm]"] * (self.df["Rotational speed [rpm]"] * 2 * np.pi / 60)
        pd.testing.assert_series_equal(self.out["power_W"], expected, check_names=False)

    def test_adds_temp_diff_k(self):
        expected = self.df["Process temperature [K]"] - self.df["Air temperature [K]"]
        pd.testing.assert_series_equal(self.out["temp_diff_K"], expected, check_names=False)

    def test_adds_wear_torque(self):
        expected = self.df["Tool wear [min]"] * self.df["Torque [Nm]"]
        pd.testing.assert_series_equal(self.out["wear_torque"], expected, check_names=False)

    def test_type_quality_mapping(self):
        mapping = {"L": 0, "M": 1, "H": 2}
        expected = self.df["Type"].map(mapping)
        pd.testing.assert_series_equal(self.out["type_quality"], expected, check_names=False)

    def test_does_not_mutate_input(self):
        original_cols = set(self.df.columns)
        engineer_features(self.df)
        assert set(self.df.columns) == original_cols

    def test_no_nan_in_engineered_columns(self):
        engineered = ["power_W", "temp_diff_K", "wear_torque", "type_quality"]
        assert self.out[engineered].isna().sum().sum() == 0


# ── build_feature_matrix ─────────────────────────────────────────────────────

class TestBuildFeatureMatrix:
    def setup_method(self):
        self.df = _make_raw_df(15)
        self.feature_names = [
            "Air temperature [K]",
            "Process temperature [K]",
            "Rotational speed [rpm]",
            "Torque [Nm]",
            "Tool wear [min]",
            "power_W",
            "temp_diff_K",
            "wear_torque",
            "type_quality",
        ]

    def test_returns_dataframe(self):
        X = build_feature_matrix(self.df, self.feature_names)
        assert isinstance(X, pd.DataFrame)

    def test_correct_columns(self):
        X = build_feature_matrix(self.df, self.feature_names)
        assert list(X.columns) == self.feature_names

    def test_correct_shape(self):
        X = build_feature_matrix(self.df, self.feature_names)
        assert X.shape == (len(self.df), len(self.feature_names))

    def test_no_nan(self):
        X = build_feature_matrix(self.df, self.feature_names)
        assert X.isna().sum().sum() == 0

    def test_subset_of_features(self):
        subset = ["power_W", "temp_diff_K"]
        X = build_feature_matrix(self.df, subset)
        assert list(X.columns) == subset


# ── load_raw ─────────────────────────────────────────────────────────────────

class TestLoadRaw:
    def test_returns_dataframe_with_correct_index(self):
        # kagglehub retourne un DataFrame avec "UDI" comme colonne ordinaire ;
        # load_raw appelle .set_index("UDI") dessus.
        raw = _make_raw_df(5).reset_index(drop=True)
        raw.insert(0, "UDI", range(1, 6))

        with patch("src.data.loader.kagglehub.load_dataset", return_value=raw) as mock_load:
            from src.data.loader import load_raw
            result = load_raw("owner/dataset", "file.csv", "UDI")

        assert isinstance(result, pd.DataFrame)
        assert result.index.name == "UDI"
        mock_load.assert_called_once()

    def test_sets_index_col(self):
        raw = _make_raw_df(5).reset_index(drop=True)
        raw.insert(0, "UDI", range(1, 6))

        with patch("src.data.loader.kagglehub.load_dataset", return_value=raw):
            from src.data.loader import load_raw
            result = load_raw("owner/dataset", "file.csv", "UDI")

        assert result.index.name == "UDI"
        assert "UDI" not in result.columns
