# =============================================================================
# Backend container — used by Hugging Face Spaces (Docker SDK).
# =============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for pypdf / fastembed (ONNX runtime needs a few system libs)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend source. (Anything outside backend/ is irrelevant to the API.)
COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/app /app/app

RUN pip install --upgrade pip \
 && pip install -e .

# Hugging Face Spaces convention: the app must listen on $PORT (defaults to 7860).
ENV PORT=7860

# On HF Spaces the only writable directory on the free tier is /tmp; on Spaces
# with the (paid) persistent-storage addon, /data is mounted and survives
# restarts. The settings below default to /data and fall back gracefully.
ENV DATABASE_PATH=/data/data.sqlite \
    STORAGE_DIR=/data/storage \
    TMP_DIR=/data/tmp \
    FASTEMBED_CACHE_PATH=/data/fastembed_cache

EXPOSE 7860

# Pre-warm the embedding model so the first request is fast. This downloads
# ~70 MB on first build; the layer is cached afterwards.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

CMD ["sh", "-c", "mkdir -p /data/storage /data/tmp /data/fastembed_cache && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
