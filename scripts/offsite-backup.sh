#!/bin/sh
set -eu

required_file() {
    name="$1"
    path="$2"
    if [ ! -s "${path}" ]; then
        echo "[$(date -u +%FT%TZ)] ERROR: ${name} secret file is missing or empty" >&2
        exit 1
    fi
}

required_file RESTIC_PASSWORD_FILE "${RESTIC_PASSWORD_FILE:-}"

if [ -n "${AWS_ACCESS_KEY_ID_FILE:-}" ]; then
    required_file AWS_ACCESS_KEY_ID_FILE "${AWS_ACCESS_KEY_ID_FILE}"
    AWS_ACCESS_KEY_ID="$(tr -d '\r\n' < "${AWS_ACCESS_KEY_ID_FILE}")"
    export AWS_ACCESS_KEY_ID
fi

if [ -n "${AWS_SECRET_ACCESS_KEY_FILE:-}" ]; then
    required_file AWS_SECRET_ACCESS_KEY_FILE "${AWS_SECRET_ACCESS_KEY_FILE}"
    AWS_SECRET_ACCESS_KEY="$(tr -d '\r\n' < "${AWS_SECRET_ACCESS_KEY_FILE}")"
    export AWS_SECRET_ACCESS_KEY
fi

if ! restic snapshots >/dev/null 2>&1; then
    if [ "${RESTIC_AUTO_INIT:-false}" != "true" ]; then
        echo "[$(date -u +%FT%TZ)] ERROR: backup repository is unavailable or uninitialized; set RESTIC_AUTO_INIT=true only for the first controlled deployment" >&2
        exit 1
    fi
    restic init
fi

interval="${OFFSITE_BACKUP_INTERVAL_SECONDS:-86400}"

while true; do
    started="$(date -u +%FT%TZ)"
    echo "[${started}] starting encrypted off-host backup"
    restic backup /data \
        --tag progyx-production \
        --host "${BACKUP_HOST_LABEL:-progyx-production}"
    restic check --read-data-subset="${RESTIC_CHECK_SUBSET:-5%}"
    restic forget \
        --tag progyx-production \
        --keep-daily "${RESTIC_KEEP_DAILY:-14}" \
        --keep-weekly "${RESTIC_KEEP_WEEKLY:-8}" \
        --keep-monthly "${RESTIC_KEEP_MONTHLY:-12}" \
        --prune
    date +%s > /tmp/offsite-last-success
    echo "[$(date -u +%FT%TZ)] encrypted off-host backup complete"
    if [ "${OFFSITE_BACKUP_RUN_ONCE:-false}" = "true" ]; then
        exit 0
    fi
    sleep "${interval}"
done
