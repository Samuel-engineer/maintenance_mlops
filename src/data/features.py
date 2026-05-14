"""Feature engineering physique basé sur les conditions de failure AI4I."""
from __future__ import annotations

import numpy as np
import pandas as pd


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit les features dérivées à partir des mesures capteurs brutes.

    Features créées :
        power_W      : puissance mécanique (W) — indicateur PWF
        temp_diff_K  : écart T_process − T_air (K) — indicateur HDF
        wear_torque  : usure × couple (min·Nm) — indicateur OSF
        type_quality : encodage ordinal L=0 / M=1 / H=2
    """
    out = df.copy()
    out["power_W"]      = out["Torque [Nm]"] * (out["Rotational speed [rpm]"] * 2 * np.pi / 60)
    out["temp_diff_K"]  = out["Process temperature [K]"] - out["Air temperature [K]"]
    out["wear_torque"]  = out["Tool wear [min]"] * out["Torque [Nm]"]
    out["type_quality"] = out["Type"].map({"L": 0, "M": 1, "H": 2})
    return pd.DataFrame(out)


def build_feature_matrix(df: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    """Applique le feature engineering et retourne la matrice X."""
    return pd.DataFrame(engineer_features(df)[feature_names])
