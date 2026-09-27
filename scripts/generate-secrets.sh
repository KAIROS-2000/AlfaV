#!/bin/sh
set -eu

target="${1:-}"
if [ -z "${target}" ]; then
    echo "usage: $0 <empty-target-directory>" >&2
    exit 2
fi

case "${target}" in
    /|/etc|/usr|/var|/home|/root)
        echo "refusing unsafe target directory: ${target}" >&2
        exit 2
        ;;
esac

mkdir -p "${target}"
for name in postgres_password redis_password judge_runner_token restic_password backup_access_key_id backup_secret_access_key; do
    if [ -e "${target}/${name}" ]; then
        echo "refusing to overwrite existing secret: ${target}/${name}" >&2
        exit 1
    fi
done

command -v openssl >/dev/null 2>&1 || {
    echo "openssl is required" >&2
    exit 1
}

umask 077
openssl rand -hex 32 > "${target}/postgres_password"
openssl rand -hex 32 > "${target}/redis_password"
openssl rand -hex 32 > "${target}/judge_runner_token"
openssl rand -hex 32 > "${target}/restic_password"
openssl rand -hex 16 > "${target}/backup_access_key_id"
openssl rand -hex 32 > "${target}/backup_secret_access_key"

echo "generated six secret files in ${target}; values were not printed"
