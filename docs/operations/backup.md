# Backup architecture (P0-8)

## Summary

| Attribute          | Value                                                     |
| ------------------ | --------------------------------------------------------- |
| Database           | Postgres 17 (service `db` in `compose.yml`)        |
| Backup tool        | `pg_dump --format=custom` (see `scripts/backup.sh`)       |
| Scheduler          | Sidecar service `db-backup` running a sleep-loop          |
| Cadence            | Every 24h from container start (configurable)             |
| On-disk format     | `progyx-<UTC timestamp>.sql.custom.gz`                    |
| Checksum sidecar   | `progyx-<UTC timestamp>.sql.custom.gz.sha256`             |
| Local location     | Named volume `postgres_backups` mounted at `/backups`     |
| Off-host copy      | Encrypted Restic service `offsite-backup`                 |
| Retention          | `BACKUP_RETENTION_DAYS` (default 14). Newest kept always. |
| Restore tool       | `scripts/restore.sh` (wraps `pg_restore --clean --if-exists`) |

## Sidecar design

The `db-backup` service is the same `postgres:17` image as the primary DB,
so `pg_dump` and `pg_restore` are guaranteed to match the server version
exactly. It runs as a simple `sh` loop:

```sh
while true; do
          sh /usr/local/bin/backup.sh || echo "backup failed"
    sleep ${BACKUP_INTERVAL_SECONDS:-86400}
done
```

The container waits for `db` to be healthy before taking the first dump
(via `depends_on.condition: service_healthy`). If a dump fails, the error
is logged to the container stdout and the loop continues — a single
failure never halts the schedule.

### Why a loop and not cron?

The `postgres:17` image is Debian-based and does not ship `cron`. Adding
`cron` via `apt-get` would expand the image surface; switching to an
alpine-based image would force us to install `postgresql-client` which then
risks version drift with the server. A sleep-loop is simpler and matches
the RPO (24 h) exactly. If sub-daily RPO is ever required, switch to
`supercronic` or a systemd timer on the host.

## Configuration

Environment variables (set on the `db-backup` service in
`compose.yml`):

| Var                         | Default    | Meaning                                |
| --------------------------- | ---------- | -------------------------------------- |
| `PGHOST`                    | `db`       | Server hostname                         |
| `PGDATABASE`                | `codequest`| Database name                           |
| `PGUSER`                    | `codequest`| Role with read access                   |
| `PGPASSWORD_FILE`           | `/run/secrets/postgres_password` | Secret file read by the sidecar entrypoint and exported as `PGPASSWORD` before `pg_dump`. |
| `BACKUP_DIR`                | `/backups` | Mount point of the named volume         |
| `BACKUP_RETENTION_DAYS`     | `14`       | Age threshold for deletion              |
| `BACKUP_INTERVAL_SECONDS`   | `86400`    | Sleep between runs                      |

## Operational notes

- **Disk usage.** The named volume `postgres_backups` is local to the host
  and shares its disk budget with the Postgres data volume. Alerting on
  `>80%` used is recommended.
- **Off-host copies.** `compose.prod.yml` starts `offsite-backup`, which sends
  the Postgres dumps, media volume and audit volume to an encrypted Restic
  repository. `RESTIC_REPOSITORY` and the external secret-file paths are
  mandatory production inputs. Local backups alone do not survive host loss.
- **Repository initialization.** `RESTIC_AUTO_INIT=true` is permitted only
  during the first controlled initialization. It must remain `false` during
  normal operation so a storage outage cannot silently create an empty
  replacement repository.
- **Weekly verification.** See `docs/operations/dr.md` for the test-restore
  procedure. A backup that has never been restored is not a backup.
- **Secrets.** The scheduler reads `PGPASSWORD_FILE` from a Docker secret at
  startup. Passwords are neither logged nor passed as build arguments.
