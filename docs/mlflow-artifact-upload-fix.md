# MLflow 3.x — Correction du pipeline d'upload des artefacts

## Contexte

Le projet utilise une architecture où l'entraînement des modèles s'exécute
**localement sur l'hôte Windows**, tandis que le serveur MLflow tourne dans un
**conteneur Docker Linux**. Les artefacts (fichiers modèles) doivent transiter
du client Windows vers le serveur Docker.

```
[Host Windows]                    [Docker network]
  train_stage1.py  ──HTTP──▶  mlflow:5000  ──▶  /mlartifacts/
  train_stage2.py                                 (volume bind → ./mlartifacts)
                                    ▲
                            [api container]
                          load_model via HTTP
```

---

## Chronologie des problèmes rencontrés

### 1. `MlflowException: API 404 /api/2.0/mlflow/logged-models`

**Symptôme**

```
mlflow.exceptions.MlflowException: API request to endpoint
/api/2.0/mlflow/logged-models failed with error code 404 != 200.
```

**Cause**

Le client MLflow installé dans le `.venv` était en version **3.12.0**, mais
l'image Docker du serveur était `ghcr.io/mlflow/mlflow:v2.13.0`. L'endpoint
`/api/2.0/mlflow/logged-models` n'existe pas en version 2.x.

**Correction**

```yaml
# docker-compose.yml
image: ghcr.io/mlflow/mlflow:v3.12.0
```

```
# requirements.txt et api/requirements.txt
mlflow>=3.12.0
```

---

### 2. `403 Invalid Host header — possible DNS rebinding attack`

**Symptôme** (logs API)

```
WARNING — MLflow indisponible (API request to endpoint
/api/2.0/mlflow/registered-models/alias failed with error code 403 != 200.
Response body: 'Invalid Host header - possible DNS rebinding attack detected')
```

**Cause**

MLflow 3.x introduit une protection anti-DNS rebinding. Quand le conteneur
`api` appelle `http://mlflow:5000`, l'en-tête `Host` vaut `mlflow`. Le serveur
MLflow ne reconnaissait que `localhost` et `127.0.0.1`.

**Correction**

```yaml
# docker-compose.yml — commande mlflow server
--allowed-hosts mlflow:5000,localhost:5000,127.0.0.1:5000
```

---

### 3. Healthchecks cassés — `curl: executable file not found`

**Symptôme**

Les conteneurs `mlflow` et `api` restaient en état `unhealthy` indéfiniment.
Le conteneur `api` dépendant de `mlflow: condition: service_healthy`, il ne
démarrait jamais correctement.

**Cause**

`curl` n'est pas présent dans `ghcr.io/mlflow/mlflow:v3.12.0` ni dans
`python:3.11-slim` (image de base de l'API).

**Correction**

```yaml
# docker-compose.yml — healthcheck mlflow
healthcheck:
  test: ["CMD", "python", "-c",
         "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]

# docker-compose.yml — healthcheck api
healthcheck:
  test: ["CMD", "python", "-c",
         "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
```

---

### 4. `No such artifact: ''` — Artefacts non uploadés

**Symptôme** (logs API au démarrage)

```
WARNING — MLflow indisponible (No such artifact: '') — tentative de chargement local
ERROR   — Échec du chargement local : [Errno 2] No such file or directory:
           'artifacts/models/stage1_pipeline.pkl'
```

**Diagnostic**

```python
# Inspection de l'entité Logged Model
GET /api/2.0/mlflow/logged-models/{model_id}
→ "artifact_location": "/mlartifacts/1/models/m-xxx/artifacts"
→ "files": []   # aucun fichier présent
```

Le dossier `./mlartifacts` était vide sur l'hôte ET dans le conteneur.

**Cause (multi-couches)**

#### 4a. Volumes manquants dans docker-compose

Le service `mlflow` n'avait pas de section `volumes:`. La base SQLite et les
artefacts étaient dans le stockage éphémère du conteneur et perdus à chaque
recréation.

```yaml
# Correction : ajout des volumes dans docker-compose.yml
volumes:
  - mlflow_db:/mlflow          # persistance SQLite
  - ./mlartifacts:/mlartifacts # persistance artefacts sur l'hôte
```

#### 4b. `--serve-artifacts` absent → client écrit en chemin local Linux

Sans `--serve-artifacts`, le client MLflow reçoit l'`artifact_location` brute
(`/mlartifacts/...`) et essaie d'y écrire **localement sur l'hôte Windows**.
Ce chemin n'existe pas sous Windows → échec silencieux, aucun fichier écrit.

```yaml
# Correction : activer le proxy HTTP d'artefacts
--serve-artifacts
--artifacts-destination /mlartifacts
--default-artifact-root mlflow-artifacts:/
```

Avec `--serve-artifacts`, le client uploade via :
```
PUT http://localhost:5000/api/2.0/mlflow-artifacts/artifacts?...
```
Le serveur stocke le fichier dans `/mlartifacts` (bind-monté → `./mlartifacts`).

#### 4c. `artifact_location` de l'expérience figée en base

L'expérience `predictive_maintenance` (id=1) avait été créée avec l'ancienne
config (`--default-artifact-root /mlartifacts`). MLflow stocke
l'`artifact_location` par expérience dans la DB SQLite. Ce champ n'est pas
modifiable via l'API REST.

```bash
# Vérification
python -c "
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
client = mlflow.MlflowClient()
exp = client.get_experiment_by_name('predictive_maintenance')
print(exp.artifact_location)
# → /mlartifacts/1   ← chemin local Linux, INCORRECT pour un client Windows
"
```

Même après avoir corrigé `--default-artifact-root`, les nouveaux logged models
héritaient de la mauvaise valeur :

```
GET /api/2.0/mlflow/logged-models/{id}
→ artifact_location: /mlartifacts/1/models/m-xxx/artifacts  ← TOUJOURS FAUX
```

**Correction** — mise à jour directe en SQLite via un script Python exécuté
dans le conteneur :

```python
# fix_artifact_location.py (exécuté via docker exec)
import sqlite3
conn = sqlite3.connect('/mlflow/mlflow.db')
conn.execute(
    "UPDATE experiments SET artifact_location=? WHERE experiment_id=?",
    ('mlflow-artifacts:/1', '1')
)
conn.commit()
conn.close()
```

```bash
docker cp fix_artifact_location.py mlflow:/tmp/fix.py
docker exec mlflow python /tmp/fix.py
```

Après correction, les nouveaux logged models reçoivent :
```
artifact_location: mlflow-artifacts:/1/models/m-xxx/artifacts
```
Le client utilise alors le proxy HTTP → upload réussi.

#### 4d. Alias `champion` jamais assigné

Les scripts d'entraînement enregistraient les modèles dans le Registry
(`registered_model_name=...`) mais n'assignaient pas l'alias. Le `predictor.py`
charge via `models:/name@champion` → `No such artifact` si l'alias n'existe pas.

```python
# Correction dans train_stage1.py et train_stage2.py
# Après mlflow.sklearn.log_model(...)
_client = mlflow.MlflowClient()
_versions = _client.search_model_versions(
    f"name='{model_name}' and run_id='{run.info.run_id}'"
)
if _versions:
    _client.set_registered_model_alias(model_name, "champion", _versions[0].version)
```

---

### 5. nginx — absence de proxy `/api` vers le conteneur API

**Symptôme**

En production (Docker), les appels de l'app frontend vers `/api/predict`
retournaient 404. En développement (Vite), le proxy `/api → localhost:8000`
fonctionnait correctement.

**Cause**

La config nginx générée dans `app/Dockerfile` ne gérait que les fichiers
statiques (SPA fallback). Aucune règle de routage pour `/api`.

**Correction**

```dockerfile
# app/Dockerfile — location /api/ ajoutée
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location /api/ {\n\
        proxy_pass http://api:8000/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/app.conf
```

---

### 6. CORS — origines mal configurées

**Symptôme**

Le navigateur bloquait les réponses de l'API (pas d'en-tête
`Access-Control-Allow-Origin`).

**Cause**

`http://localhost:80` dans `CORS_ORIGINS`. Les navigateurs omettent le port
par défaut (80) dans l'en-tête `Origin` : l'en-tête envoyé est `http://localhost`.
FastAPI's CORSMiddleware fait une comparaison de chaîne exacte → aucune
correspondance → rejet silencieux.

**Correction**

```yaml
# docker-compose.yml
CORS_ORIGINS: http://localhost,http://app
```

---

## Configuration finale fonctionnelle

### `docker-compose.yml` — service mlflow

```yaml
mlflow:
  image: ghcr.io/mlflow/mlflow:v3.12.0
  hostname: mlflow
  command: >
    mlflow server
    --host 0.0.0.0
    --port 5000
    --backend-store-uri sqlite:///mlflow/mlflow.db
    --serve-artifacts
    --artifacts-destination /mlartifacts
    --default-artifact-root mlflow-artifacts:/
    --allowed-hosts mlflow:5000,localhost:5000,127.0.0.1:5000
  volumes:
    - mlflow_db:/mlflow
    - ./mlartifacts:/mlartifacts
  healthcheck:
    test: ["CMD", "python", "-c",
           "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]
```

### Flux d'upload des artefacts (après correction)

```
train_stage1.py (Windows)
  │
  ├─ mlflow.set_tracking_uri("http://localhost:5000")
  ├─ mlflow.sklearn.log_model(name="stage1_pipeline", ...)
  │     │
  │     ├─ POST /api/2.0/mlflow/logged-models
  │     │   → artifact_location: mlflow-artifacts:/1/models/m-xxx/artifacts
  │     │
  │     └─ PUT http://localhost:5000/api/2.0/mlflow-artifacts/artifacts
  │             → stocké dans /mlartifacts/1/models/m-xxx/artifacts
  │               (bind-monté → ./mlartifacts/ sur l'hôte)
  │
  └─ set_registered_model_alias("maintenance_stage1", "champion", version)
```

### Flux de chargement (API Docker)

```
api container (démarrage)
  │
  └─ mlflow.sklearn.load_model("models:/maintenance_stage1@champion")
        │
        ├─ GET http://mlflow:5000/api/2.0/mlflow/registered-models/alias
        │   → source: models:/m-xxx
        │
        ├─ GET http://mlflow:5000/api/2.0/mlflow/logged-models/m-xxx
        │   → artifact_location: mlflow-artifacts:/1/models/m-xxx/artifacts
        │
        └─ GET http://mlflow:5000/api/2.0/mlflow-artifacts/artifacts/...
            → télécharge model.pkl, MLmodel, etc.
```

---

## Points de vigilance pour les futures installations

1. **Toujours vérifier la version client/serveur MLflow** — une différence
   majeure (2.x vs 3.x) casse la compatibilité API.

2. **`--serve-artifacts` nécessite `--default-artifact-root mlflow-artifacts:/`**
   et non un chemin filesystem — sinon les clients non-Linux ne peuvent pas écrire.

3. **L'`artifact_location` d'une expérience est immuable via l'API REST.**
   Si le serveur MLflow est reconfiguré après la création de l'expérience, il
   faut mettre à jour directement la base SQLite.

4. **Ne pas utiliser `curl` dans les healthchecks** des images basées sur
   `python:*-slim` ou `ghcr.io/mlflow/mlflow:*` — utiliser
   `python -c "import urllib.request; urllib.request.urlopen(...)"`.

5. **`artifact_path` est déprécié dans MLflow 3.x** — utiliser uniquement
   `name=` dans `log_model()`.
