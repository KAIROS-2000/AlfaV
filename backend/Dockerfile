# syntax=docker/dockerfile:1.7
FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1
COPY backend/requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && pip install -r /tmp/requirements.txt \
    && useradd --create-home --uid 1001 --shell /usr/sbin/nologin appuser
# Stable binary/static assets are copied before Python application code.
COPY backend/sprite /app/backend/sprite
COPY media/avatars /app/media/avatars
COPY media/frames /app/media/frames
COPY backend/app /app/backend/app
COPY backend/run.py /app/backend/run.py
COPY backend/entrypoint.sh /usr/local/bin/backend-entrypoint
COPY shared /app/shared
RUN mkdir -p /media /app/backend/logs/audit \
    && chown -R appuser:appuser /media /app/backend/logs \
    && chmod 0555 /usr/local/bin/backend-entrypoint
WORKDIR /app/backend
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=2).read()"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2", "--timeout", "45", "--graceful-timeout", "30", "--max-requests", "1000", "--max-requests-jitter", "100", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "run:app"]
