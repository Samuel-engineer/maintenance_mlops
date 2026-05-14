"""
FastAPI — Application principale.

Démarrage :
    uvicorn api.main:app --reload

Endpoints :
    GET  /health          → statut de l'API et état des modèles
    POST /predict         → prédiction à partir de mesures capteurs brutes
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers.predict import router as predict_router
from api.routers.predict import load_predictor, get_model_info

# logging.basicConfig est appelé ici uniquement si ce module est le point d'entrée.
# En production (uvicorn --log-config ...), uvicorn configure le logging lui-même.
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    )
logger = logging.getLogger(__name__)

_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge les modèles une seule fois au démarrage."""
    try:
        load_predictor()
        logger.info("Modèles chargés avec succès")
    except Exception as exc:
        logger.error("Échec du chargement des modèles : %s", exc)
        # On laisse l'app démarrer ; /health exposera l'état dégradé
    yield
    logger.info("Arrêt de l'application")


app = FastAPI(
    title="Maintenance Prédictive API",
    description="Détection et diagnostic de pannes machine — Architecture deux étapes",
    version=settings.api_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(predict_router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    """
    Retourne le statut de l'API, l'état des modèles, la version et l'uptime.
    HTTP 200 même si les modèles sont absents — laisser au load-balancer
    le soin d'interpréter le champ `models_loaded`.
    """
    info = get_model_info()
    return {
        "status": "ok" if info["models_loaded"] else "degraded",
        "version": settings.api_version,
        "uptime_seconds": round(time.time() - _start_time, 1),
        **info,
    }
