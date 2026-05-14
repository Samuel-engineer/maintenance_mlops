"""Chargement du dataset AI4I 2020 depuis Kaggle Hub."""
from __future__ import annotations

import pandas as pd
import kagglehub
from kagglehub import KaggleDatasetAdapter


def load_raw(kaggle_dataset: str, kaggle_file: str, index_col: str) -> pd.DataFrame:
    """Télécharge (ou utilise le cache) et retourne le DataFrame brut."""
    df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        kaggle_dataset,
        kaggle_file,
    ).set_index(index_col)
    return df
