"""
Paramètres de configuration de l'API chargés depuis les variables d'environnement.

Variables d'environnement disponibles (peuvent être définies dans un fichier .env) :
    CORS_ORIGINS          : liste des origines autorisées, séparées par des virgules
                            ex. "http://localhost:5173,https://app.example.com"
    MLFLOW_TRACKING_URI   : URI du serveur MLflow
    MODEL_ALIAS           : alias du modèle dans le Registry (défaut : "champion")
    API_VERSION           : version de l'API (défaut : "1.0.0")
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_origins: str = "http://localhost:5173"
    mlflow_tracking_uri: str = "http://localhost:5000"
    model_alias: str = "champion"
    api_version: str = "1.0.0"

    @property
    def cors_origins_list(self) -> list[str]:
        """Retourne la liste des origines CORS parsée depuis la chaîne CSV."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
