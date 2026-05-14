"""Schémas Pydantic — entrées et sorties de l'API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SensorReading(BaseModel):
    """
    Mesures brutes transmises par les capteurs de la machine.

    Les champs utilisent des noms snake_case comme interface publique.
    `to_raw_dict()` traduit vers les noms de colonnes attendus par
    `engineer_features()` (noms du dataset AI4I).
    """

    product_type: Literal["L", "M", "H"] = Field(
        ..., description="Qualité du produit : L (low) / M (medium) / H (high)"
    )
    air_temperature_k: float = Field(
        ..., ge=290.0, le=320.0, description="Température de l'air [K]"
    )
    process_temperature_k: float = Field(
        ..., ge=295.0, le=325.0, description="Température du processus [K]"
    )
    rotational_speed_rpm: int = Field(
        ..., ge=0, le=3000, description="Vitesse de rotation [rpm]"
    )
    torque_nm: float = Field(
        ..., ge=0.0, le=120.0, description="Couple [Nm]"
    )
    tool_wear_min: int = Field(
        ..., ge=0, le=300, description="Usure de l'outil [min]"
    )

    @model_validator(mode="after")
    def process_temp_above_air(self) -> "SensorReading":
        if self.process_temperature_k <= self.air_temperature_k:
            raise ValueError(
                "process_temperature_k doit être supérieure à air_temperature_k"
            )
        return self

    def to_raw_dict(self) -> dict:
        """Traduit vers les noms de colonnes attendus par engineer_features()."""
        return {
            "Type":                    self.product_type,
            "Air temperature [K]":     self.air_temperature_k,
            "Process temperature [K]": self.process_temperature_k,
            "Rotational speed [rpm]":  self.rotational_speed_rpm,
            "Torque [Nm]":             self.torque_nm,
            "Tool wear [min]":         self.tool_wear_min,
        }


class PredictionResponse(BaseModel):
    failure_proba: float = Field(..., ge=0.0, le=1.0, description="Probabilité de panne (Stage 1)")
    failure_alert: bool = Field(..., description="True si la probabilité dépasse le seuil optimisé")
    failure_types: list[str] = Field(..., description="Types de pannes détectés (Stage 2)")
    recommended_actions: list[str] = Field(..., description="Actions de maintenance associées")
