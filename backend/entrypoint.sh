#!/bin/sh
set -eu

TARGET_DIR=/run/app-secrets
install -d -m 0750 "${TARGET_DIR}"
chown 0:1001 "${TARGET_DIR}"

install_secret() {
    source="$1"
    target="$2"
    if [ ! -s "${source}" ]; then
        echo "backend entrypoint: required secret source is missing or empty" >&2
        exit 1
    fi
    install -m 0400 "${source}" "${target}"
    chown 1001:1001 "${target}"
}

install_secret /run/secrets/postgres_password "${TARGET_DIR}/postgres_password"
install_secret /run/secrets/redis_password "${TARGET_DIR}/redis_password"
install_secret /run/secrets/judge_runner_token "${TARGET_DIR}/judge_runner_token"

# One-shot provisioning may mount an additional root-owned 0600 password file.
# Copy it into the private tmpfs before dropping privileges, just like the
# long-lived application secrets.
if [ -n "${PROVISION_SUPERADMIN_PASSWORD_FILE:-}" ]; then
    install_secret "${PROVISION_SUPERADMIN_PASSWORD_FILE}" "${TARGET_DIR}/initial_superadmin_password"
    export PROVISION_SUPERADMIN_PASSWORD_FILE="${TARGET_DIR}/initial_superadmin_password"
fi

# The container starts only long enough to copy bind-mounted Compose secrets,
# then irrevocably executes the application as the image's non-root UID/GID.
exec setpriv --reuid=1001 --regid=1001 --init-groups --no-new-privs "$@"
