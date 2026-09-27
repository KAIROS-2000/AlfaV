# Production release gate

Production deploys must use one reviewed Git SHA, immutable image digests, an
external environment file, external secret files, TLS ingress and encrypted
off-host backups. The development `.env` is never a production input.

## Required operator inputs

Copy `.env.production.example` to a protected location outside the checkout and
replace every placeholder. Required external decisions are:

- public DNS hostname and ACME contact;
- approved legal operator identity, contacts and versioned legal documents;
- counsel-approved legal basis and parental-consent model for minor registration;
- transactional email provider key and verified sender domain;
- DB, Redis, JWT, judge and backup credentials;
- encrypted Restic repository and object-storage credentials;
- an owned Yandex Disk tournament XLSX source, data owner and update SLA;
- immutable backend/frontend/judge image digests;
- primary/secondary on-call and incident commander contacts.

The historical GigaChat credential incident in `security-followups.md` must be
closed by the credential owner before release. Source code keeps the endpoint
disabled, but source changes cannot revoke an external credential.

The release attestation flags in the
production environment are release attestations, not bypasses. Set each to
`true` only after its legal approval, incident closure, Linux sandbox check,
restore drill, on-call review, mail canary, observability or backup-alert
evidence has been archived.

The launch scope contains no payment processing: `/parent/billing` is an
explicit `not_connected` status and cannot create charges. Do not advertise
subscriptions, payments or refunds until a provider, webhook idempotency,
reconciliation and refund flow have their own reviewed release.

`TOURNAMENT_YANDEX_PUBLIC_URL` is mandatory in production and restricted to an
HTTPS Yandex Disk public host. The data owner must monitor XLSX freshness/schema
and treat the in-app cached snapshot warning as a degraded state.

## Preflight

```sh
sh scripts/production-preflight.sh /secure/path/progyx-production.env
```

The command rejects development flags, local/placeholder values, missing or
short secret files, mutable application image tags, disabled mail verification,
uninitialized backup mode and invalid Compose configuration. It never prints
secret values.

On deploy, `backend-init` waits for a fresh local database dump and a successful
encrypted off-site snapshot before it applies migrations. It runs `upgrade-db`
only; demo and curriculum seeding are never implicit production deployment
steps. Run any approved content import as a separate audited operation.

## First controlled backup initialization

Initialize a new Restic repository once, during a controlled maintenance step:

```sh
RESTIC_AUTO_INIT=true docker compose \
  --env-file /secure/path/progyx-production.env \
  -f compose.yml -f compose.prod.yml up pre-migration-offsite-backup
```

After initialization set `RESTIC_AUTO_INIT=false` permanently and rerun the
preflight. A repository connectivity error must fail the backup container; it
must never silently initialize a replacement repository.

## Deploy

```sh
docker compose \
  --env-file /secure/path/progyx-production.env \
  -f compose.yml -f compose.prod.yml \
  pull

docker compose \
  --env-file /secure/path/progyx-production.env \
  -f compose.yml -f compose.prod.yml \
  up -d --wait --no-build
```

Caddy is the only service publishing host ports (80/443). Frontend/backend,
PostgreSQL, Redis and judge-runner are reachable only on their least-privilege
edge, app, data and judge networks; use `docker compose exec` for diagnostics.
Caddy is the direct public ingress: it replaces browser-supplied forwarding
headers with `X-Progyx-Client-IP` derived from the peer socket. The BFF validates
that single address and sends one `X-Forwarded-For` hop to Flask. If a load
balancer or CDN is added later, define its exact address ranges and update this
trust contract; never enable a broad private-range proxy trust policy.

## Scheduled application jobs

In-process scheduler threads are disabled because Gunicorn has multiple
workers. Configure one external scheduler with an overlap lock and alert on any
non-zero exit. Run these commands from the deployed Compose directory:

```sh
docker compose --env-file /secure/path/progyx-production.env -f compose.yml -f compose.prod.yml exec -T --user 1001:1001 backend python -m flask --app run.py export-audit-logs
docker compose --env-file /secure/path/progyx-production.env -f compose.yml -f compose.prod.yml exec -T --user 1001:1001 backend python -m flask --app run.py send-weekly-parent-progress-emails
```

Schedule audit export daily and the parent digest weekly according to the
approved timezone/business calendar. Archive scheduler run IDs and delivery
counts in the monitoring system.

## First production superadmin

After the initial migration, generate a strong one-line password in an external
`0600` file and run the dedicated one-time command. The password is read from
the mounted file and is never printed:

```sh
docker compose --env-file /secure/path/progyx-production.env \
  -f compose.yml -f compose.prod.yml run --rm --no-deps -T \
  -e PROVISION_SUPERADMIN_EMAIL=owner@your-domain.example \
  -e PROVISION_SUPERADMIN_NAME='Initial platform owner' \
  -e PROVISION_SUPERADMIN_PASSWORD_FILE=/run/secrets/initial-admin-password \
  -v /secure/progyx/initial-admin-password:/run/secrets/initial-admin-password:ro \
  backend python -m flask --app run.py provision-first-superadmin
```

The command takes a PostgreSQL advisory lock, refuses to run when any
superadmin already exists, and writes an `initial_superadmin_provisioned` audit
record. Confirm login and the credential handoff/rotation policy, then securely remove
the one-time password file. Subsequent administrators must be created through
the audited superadmin UI.

## Release evidence

Archive the following against the release SHA:

- green backend, frontend, browser and Compose security checks;
- image digests and generated SPDX SBOMs;
- vulnerability-scan results or time-bounded approved waivers;
- production preflight output;
- migration revision before and after deploy;
- `/api/live` and `/api/ready` smoke results;
- transactional email canary result;
- judge isolation checklist result on the target Linux runtime;
- latest local and off-host backup timestamps;
- latest recorded restore drill;
- active alert-route test described in `observability.md`;
- rollback decision and previous image digests.

## Rollback

Application rollback uses the prior immutable image digests. Database rollback
must follow an explicitly reviewed migration recovery plan; never run an older
application against a schema unless the migration is declared backward
compatible. For destructive recovery use `docs/operations/dr.md`.
