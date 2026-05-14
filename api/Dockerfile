# ── Stage 1 : installation des dépendances ──────────────────────────────────
# Contexte de build : racine du projet (docker build -f api/Dockerfile .)
FROM python:3.11-slim AS builder

WORKDIR /build

COPY api/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 2 : image de production ────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Packages installés au stage builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Code source (mlartifacts montés en volume via docker-compose)
COPY api/    ./api/
COPY src/    ./src/
COPY config/ ./config/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

RUN adduser --disabled-password --gecos "" appuser
USER appuser

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
