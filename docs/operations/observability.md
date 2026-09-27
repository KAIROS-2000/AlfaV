# Production observability and alert gate

The repository exposes vendor-neutral signals; the operator must route them to
an off-host monitoring and paging system before setting
`OBSERVABILITY_ALERTING_VERIFIED=true` or `BACKUP_ALERTING_VERIFIED=true`.
Application containers must not hold a monitoring vendor's administrative
credential.

## Signals

- Caddy emits JSON access logs to stdout, including upstream status and latency.
- Gunicorn emits access/error logs to stdout and rotates workers with bounded
  request counts.
- `/api/live` proves the Flask process can answer.
- `/api/ready` returns non-2xx when PostgreSQL, required Redis or the isolated
  judge path is unavailable.
- Docker health covers database, Redis, runner/gateway, frontend/backend and
  backup freshness. Recurring local/off-site jobs exit on failure so restart
  counters are actionable.
- Local and off-site backup success timestamps are machine-readable in their
  container health checks; Restic output records the snapshot ID.

Collect stdout/stderr and container health/restart/resource metrics off-host.
Redact cookies, authorization headers, CSRF values, reset/setup tokens, message
bodies, uploaded filenames and learner personal data. Retention and access must
match the approved privacy policy.

## Initial SLOs and alerts

Review these after staging load tests and record any change:

| Signal | Initial objective / page condition |
| --- | --- |
| Public availability | 99.9% monthly; page after 2 consecutive failed probes |
| API 5xx | page when >2% for 5 minutes, excluding planned maintenance |
| API latency | warn when p95 >750 ms for 10 minutes; page above 2 s |
| Readiness | page immediately if non-2xx persists for 2 minutes |
| DB/Redis | page on unhealthy state, connection saturation or storage >85% |
| Judge | page on failed readiness, queue saturation, timeout spike or restart |
| Email | page on provider errors or a failed release canary |
| Local/off-site backup | page on failure/restart or age >25 hours |
| Host resources | warn at 80%, page at 90% disk/memory sustained for 10 minutes |

## Release verification

Before launch, force one synthetic 5xx/readiness failure and one backup failure
in staging, verify primary and secondary on-call delivery, acknowledge and
resolve the alerts, and archive timestamps/screenshots with the release SHA.
Also verify dashboards use the public TLS path rather than loopback-only or
container-internal probes.
