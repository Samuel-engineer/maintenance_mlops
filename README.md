# Maintenance Prédictive MLOps

Système de détection et de diagnostic de pannes machines industrielles,
exposé via une API REST et une interface web, avec tracking des expériences
ML via MLflow.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Docker network                                             │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  app     │───▶│  api         │───▶│  mlflow          │  │
│  │ nginx:80 │    │ FastAPI:8000 │    │ Tracking:5000    │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│        ▲                                      │             │
└────────┼──────────────────────────────────────┼─────────────┘
         │                                      │
    [Navigateur]                     [./mlartifacts]
                                     [mlflow_db volume]
```

| Composant | Image / Base | Rôle |
|-----------|-------------|------|
| `mlflow`  | `ghcr.io/mlflow/mlflow:v3.12.0` | Tracking server + proxy artefacts |
| `api`     | `python:3.11-slim` | API FastAPI, charge et sert les modèles |
| `app`     | `nginx:1.27-alpine` | Frontend React/Vite, proxy `/api` → `api:8000` |

## Pipeline ML

Le modèle fonctionne en **deux étapes** :

1. **Stage 1 — Détection binaire** (`maintenance_stage1`)
   - `GradientBoostingClassifier` avec SMOTE et optimisation du seuil (F2-score)
   - Prédit si la machine est en état de défaillance (`Machine failure = 1`)

2. **Stage 2 — Diagnostic multi-label** (`maintenance_stage2`)
   - `RandomForestClassifier` avec `class_weight="balanced"`
   - Identifie le type de panne parmi : `TWF`, `HDF`, `PWF`, `OSF`, `RNF`
   - Exécuté uniquement si le stage 1 détecte une défaillance

### Features utilisées

| Feature brute | Description |
|---------------|-------------|
| `Air temperature [K]` | Température de l'air |
| `Process temperature [K]` | Température du processus |
| `Rotational speed [rpm]` | Vitesse de rotation |
| `Torque [Nm]` | Couple |
| `Tool wear [min]` | Usure de l'outil |

Features calculées : `power_W`, `temp_diff_K`, `wear_torque`, `type_quality`

### Dataset

[AI4I 2020 Predictive Maintenance Dataset](https://www.kaggle.com/datasets/stephanmatzka/predictive-maintenance-dataset-ai4i-2020)
— téléchargé automatiquement via `kagglehub`.

## Prérequis

- Docker Desktop avec Docker Compose V2
- Python 3.11+ (pour l'entraînement local)
- Credentials Kaggle (`~/.kaggle/kaggle.json`) pour le téléchargement du dataset

## Installation et démarrage

### 1. Cloner et configurer l'environnement

```bash
git clone <repo>
cd maintenance_mlops
cp .env.example .env
```

### 2. Démarrer les services

```bash
docker compose up -d
```

Les services démarrent dans l'ordre : `mlflow` → `api` → `app`.  
Les healthchecks assurent que chaque service est prêt avant le suivant.

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| API | http://localhost:8000 |
| MLflow UI | http://localhost:5000 |

### 3. Entraîner les modèles

```bash
# Créer le virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Lancer l'entraînement (stage 1 puis stage 2)
python -m src.models.train_stage1
python -m src.models.train_stage2
```

Les modèles sont enregistrés dans le MLflow Registry avec l'alias `champion`
et les artefacts sont persistés dans `./mlartifacts/`.

### 4. Vérifier le déploiement

```bash
# Santé de l'API
curl http://localhost:8000/health

# Prédiction test
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "product_type": "M",
    "air_temperature_k": 298.1,
    "process_temperature_k": 308.6,
    "rotational_speed_rpm": 1551,
    "torque_nm": 42.8,
    "tool_wear_min": 0
  }'
```

## Structure du projet

```
maintenance_mlops/
├── config/
│   └── config.yaml          # Paramètres ML et noms des modèles
├── src/
│   ├── data/
│   │   ├── loader.py        # Téléchargement et chargement du dataset
│   │   └── features.py      # Feature engineering
│   ├── models/
│   │   ├── train_stage1.py  # Entraînement détection binaire
│   │   └── train_stage2.py  # Entraînement diagnostic multi-label
│   └── pipeline/
│       └── predictor.py     # Chargement des modèles et inférence
├── api/
│   ├── main.py              # Application FastAPI
│   ├── schemas.py           # Schémas Pydantic (entrées/sorties)
│   ├── config.py            # Configuration via variables d'env
│   └── routers/
│       └── predict.py       # Endpoint POST /predict
├── app/                     # Frontend React/Vite/TypeScript
├── notebooks/
│   └── predictive_maintenance.ipynb
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_data.py
│   └── test_models.py
├── mlartifacts/             # Artefacts MLflow (gitignored sauf .gitkeep)
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Variables d'environnement

Copier `.env.example` vers `.env` et adapter si besoin.

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | URI du serveur MLflow |
| `MODEL_ALIAS` | `champion` | Alias du modèle actif dans le Registry |
| `CORS_ORIGINS` | `http://localhost:5173` | Origines autorisées (dev) |

En production Docker, `MLFLOW_TRACKING_URI` est surchargé à
`http://mlflow:5000` et `CORS_ORIGINS` à `http://localhost,http://app`
directement dans `docker-compose.yml`.

## Tests

```bash
pytest tests/ -v --cov=src --cov=api
```

## MLflow

### Accéder à l'interface

http://localhost:5000

### Noms des modèles dans le Registry

| Modèle | Nom Registry |
|--------|-------------|
| Stage 1 | `maintenance_stage1` |
| Stage 2 | `maintenance_stage2` |

L'alias `champion` désigne la version active chargée par l'API au démarrage.

### Ré-entraîner et promouvoir un modèle

Relancer `train_stage1.py` et/ou `train_stage2.py` : l'alias `champion` est
automatiquement mis à jour vers la nouvelle version. Redémarrer l'API pour
prendre en compte le nouveau modèle :

```bash
docker restart api
```

## Développement frontend

```bash
cd app
npm install
npm run dev   # http://localhost:5173
```

Le proxy Vite redirige `/api/*` vers `http://localhost:8000` en dev.

## CI/CD

Le pipeline GitHub Actions (`.github/workflows/cicd.yml`) exécute :

1. **test** — `pytest` sur le code source
2. **build-api** — build et push de l'image API sur GHCR
3. **build-app** — build et push de l'image App sur GHCR

Les jobs `build-*` ne s'exécutent que sur la branche `main`.
