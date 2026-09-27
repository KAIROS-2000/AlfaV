#!/bin/sh
set -eu

ENV_FILE="${1:-}"
if [ -z "${ENV_FILE}" ] || [ ! -f "${ENV_FILE}" ]; then
    echo "usage: $0 /secure/path/progyx-production.env" >&2
    exit 2
fi

set -a
# The deployment env file is operator-controlled and must contain shell-safe KEY=VALUE lines.
# shellcheck disable=SC1090
. "${ENV_FILE}"
set +a

fail() {
    echo "production preflight failed: $*" >&2
    exit 1
}

required() {
    name="$1"
    value="$(printenv "${name}" 2>/dev/null || true)"
    [ -n "${value}" ] || fail "${name} is required"
    lowered="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]')"
    case "${lowered}" in
        *replace*|*change-me*|*placeholder*|*example.com*|*example.invalid*|*localhost*|*progyx.local*)
            fail "${name} still contains a placeholder or local value"
            ;;
    esac
}

require_secret_file() {
    name="$1"
    minimum="$2"
    path="$(printenv "${name}" 2>/dev/null || true)"
    [ -f "${path}" ] || fail "${name} does not point to a readable file"
    secret="$(tr -d '\r\n' < "${path}")"
    size="$(printf '%s' "${secret}" | wc -c | tr -d ' ')"
    [ "${size}" -ge "${minimum}" ] || fail "${name} must contain at least ${minimum} characters"
    lowered="$(printf '%s' "${secret}" | tr '[:upper:]' '[:lower:]')"
    case "${lowered}" in
        *replace*|*change-me*|*placeholder*|*example*|*local-dev*|*test-token*)
            fail "${name} points to placeholder secret material"
            ;;
    esac
    unset secret lowered
}

[ "${APP_ENV:-}" = "production" ] || fail "APP_ENV must be production"
[ "${NEXT_PUBLIC_APP_ENV:-}" = "production" ] || fail "NEXT_PUBLIC_APP_ENV must be production"
[ "${SESSION_COOKIE_SECURE:-}" = "true" ] || fail "SESSION_COOKIE_SECURE must be true"
[ "${ENABLE_DEMO_DATA:-}" = "false" ] || fail "ENABLE_DEMO_DATA must be false"
[ "${SUPERADMIN_BOOTSTRAP:-}" = "false" ] || fail "SUPERADMIN_BOOTSTRAP must be false"
[ "${SEND_MAIL:-}" = "true" ] || fail "SEND_MAIL must be true"
[ "${EMAIL_DRY_RUN:-}" = "false" ] || fail "EMAIL_DRY_RUN must be false"
[ "${TRUST_PROXY:-}" = "true" ] || fail "TRUST_PROXY must be true behind the bundled ingress"
[ "${RESTIC_AUTO_INIT:-false}" = "false" ] || fail "RESTIC_AUTO_INIT must be false after controlled repository initialization"

for attestation in \
    LEGAL_DOCUMENTS_APPROVED MINOR_REGISTRATION_LEGAL_BASIS_APPROVED \
    HISTORICAL_GIGACHAT_INCIDENT_CLOSED \
    JUDGE_SANDBOX_HOST_VERIFIED RESTORE_DRILL_VERIFIED ONCALL_RUNBOOK_READY \
    TRANSACTIONAL_EMAIL_CANARY_VERIFIED OBSERVABILITY_ALERTING_VERIFIED \
    BACKUP_ALERTING_VERIFIED; do
    value="$(printenv "${attestation}" 2>/dev/null || true)"
    [ "${value}" = "true" ] || fail "${attestation} must be true and backed by release evidence"
done

case "${PUBLIC_ORIGIN:-}" in
    https://*) ;;
    *) fail "PUBLIC_ORIGIN must be an https origin" ;;
esac

[ "${PUBLIC_ORIGIN}" = "https://${PUBLIC_DOMAIN:-}" ] || fail "PUBLIC_ORIGIN must be exactly https://PUBLIC_DOMAIN with no path, query or fragment"
[ "${NEXT_PUBLIC_SITE_URL:-}" = "${PUBLIC_ORIGIN}" ] || fail "NEXT_PUBLIC_SITE_URL must equal PUBLIC_ORIGIN"

for name in \
    PUBLIC_DOMAIN PUBLIC_ORIGIN ACME_EMAIL SECRET_KEY JWT_SIGNING_KEY_ID JWT_SIGNING_KEYS \
    BACKEND_IMAGE FRONTEND_IMAGE JUDGE_RUNNER_IMAGE POSTGRES_IMAGE CADDY_IMAGE RESTIC_IMAGE \
    UNISENDER_GO_API_KEY EMAIL_FROM \
    LEGAL_OPERATOR_NAME LEGAL_OPERATOR_TAX_ID LEGAL_OPERATOR_REGISTRATION_ID \
    LEGAL_OPERATOR_ADDRESS LEGAL_SUPPORT_EMAIL LEGAL_SUPPORT_PHONE LEGAL_DOCUMENTS_VERSION \
    LEGAL_PRIVACY_CONTENT LEGAL_TERMS_CONTENT LEGAL_PERSONAL_DATA_CONTENT \
    TOURNAMENT_YANDEX_PUBLIC_URL \
    RESTIC_REPOSITORY; do
    required "${name}"
done

for name in BACKEND_IMAGE FRONTEND_IMAGE JUDGE_RUNNER_IMAGE POSTGRES_IMAGE CADDY_IMAGE RESTIC_IMAGE; do
    value="$(printenv "${name}")"
    case "${value}" in
        *@sha256:*) ;;
        *) fail "${name} must use an immutable @sha256 digest" ;;
    esac
done

for name in POSTGRES_PASSWORD_FILE_HOST REDIS_PASSWORD_FILE_HOST JUDGE_RUNNER_TOKEN_FILE_HOST RESTIC_PASSWORD_FILE_HOST; do
    require_secret_file "${name}" 32
done
require_secret_file BACKUP_ACCESS_KEY_ID_FILE_HOST 16
require_secret_file BACKUP_SECRET_ACCESS_KEY_FILE_HOST 32

docker compose --env-file "${ENV_FILE}" -f compose.yml -f compose.prod.yml config --quiet

echo "production preflight passed"
