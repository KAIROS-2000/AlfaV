# syntax=docker/dockerfile:1.7
# Copy the exact same Debian Node runtime used by the frontend. This avoids
# relying on a package version that can disappear from Debian repositories.
FROM node:22-bookworm-slim@sha256:d649c27dae7ba0137b3cef5dd75baa422c08dc3d9e3fc0c23dfb172dc3cc6436 AS node-runtime

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
WORKDIR /app
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 judgeuser \
    && useradd --system --uid 1001 --gid 1001 --home-dir /home/judgeuser --create-home --shell /usr/sbin/nologin judgeuser
COPY judge_runner/app.py /app/judge_runner/app.py
COPY judge_runner/network_isolation_smoke.py /app/judge_runner/network_isolation_smoke.py
COPY shared /app/shared
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    JUDGE_RUNNER_HOST=0.0.0.0 \
    JUDGE_RUNNER_PORT=8090
CMD ["python", "judge_runner/app.py"]
