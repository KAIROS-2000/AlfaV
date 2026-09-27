# Image pinning (P0-6)

Production builds MUST pin every base image by digest (`@sha256:<digest>`)
rather than by mutable tag. Floating tags (`postgres:17`, `python:3.12-slim`,
`node:22-bookworm-slim`, ...) can silently change base OS packages under us,
which defeats reproducible builds and SBOM/CVE tracking. Production Compose
uses only the six release images recorded by immutable registry digest.

## Images tracked by this repo

| Pinned base | Derived/runtime use |
| --- | --- |
| `postgres:17` | `postgres/Dockerfile`; produces `progyx-postgres` for `db` and all PostgreSQL backup services |
| `python:3.12-slim` | `backend/Dockerfile`, `judge_runner/Dockerfile` |
| `node:22-bookworm-slim` | `frontend/Dockerfile` and the judge JavaScript runtime |
| `golang:1.26.6-alpine` | Rebuilds gosu 1.19, Caddy v2.11.4, and Restic v0.19.1 |
| `redis:7-alpine` | `compose.yml` service `redis`; CI `services.redis` |
| `caddy:2-alpine` | Final runtime base for `progyx-caddy`, used by public ingress and judge gateway |
| `restic/restic:0.19.1` | Final runtime base for `progyx-restic`, used by encrypted off-site backup services |

CI-only security tools (Gitleaks, Trivy and Syft) are pinned directly in the
workflow as well. Review those digests when their workflow versions change.

Any change to this list MUST be reflected in `scripts/pin-images.sh`.

## Resolving digests

```sh
./scripts/pin-images.sh
```

This pulls each image from its configured registry and prints its current
`<repo>@sha256:<digest>` to stdout. Example output:

```
python@sha256:1234...abcd  # pinned from python:3.12-slim
node@sha256:5678...ef01    # pinned from node:22-bookworm-slim
postgres@sha256:9abc...def0  # pinned from postgres:17
```

Equivalent manual commands (run one per image):

```sh
docker pull python:3.12-slim
docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
```

## Applying digests

1. Run `scripts/pin-images.sh` and capture the output.
2. Replace each occurrence in the files listed in the table above:
   - `FROM python:3.12-slim` → `FROM python:3.12-slim@sha256:<digest>`
   - `FROM postgres:17` → `FROM postgres:17@sha256:<digest>` in `postgres/Dockerfile`
   - `FROM golang:1.26.6-alpine` → `FROM golang:1.26.6-alpine@sha256:<digest>` in all three Go build stages
   - `FROM node:22-bookworm-slim AS deps` → `FROM node:22-bookworm-slim@sha256:<digest> AS deps`
     (and identically for the `builder` and `runner` stages — they MUST share
     the same digest so that the multi-stage build is coherent).
3. Commit the change with a message like
   `chore(deps): pin container images (YYYY-MM-DD)` and record the digests in
   the commit body for audit.
4. Rebuild locally and run the full test suite before merging.

Release tags run `.github/workflows/release.yml`. The workflow first pushes each
application image under a quarantine `candidate-<sha>` tag with provenance and
SBOM metadata, scans that exact registry digest, and records it as an artifact.
Only after all six candidates (`frontend`, `backend`, `judge-runner`,
`postgres`, `caddy`, and `restic`) pass does one promotion job sign those
digests with GitHub OIDC and attach the release/source-SHA tags without
rebuilding. Production preflight requires all six `*_IMAGE` values to be the
recorded `@sha256:` references.

## Cadence

- **Monthly** renewal: re-run `scripts/pin-images.sh` and bump to the latest
  tag digests; inspect release notes for breaking changes.
- **Ad-hoc** renewal: whenever a CVE affecting a pinned image is announced,
  rotate immediately. Track the rotation in the security log.

## Judge-runner Node runtime

`judge_runner/Dockerfile` copies only the Node executable from the same
digest-pinned `node:22-bookworm-slim` stage as the frontend. Global npm/Yarn
packages are intentionally absent from the judge runtime. Validate Python and
JavaScript submissions after every Node digest update.

Application runtime stages install the latest security updates published for
their pinned Debian release before the application is copied. This protects a
release when an upstream base digest has not yet been rebuilt after a Debian
security advisory. Consequently, the base digest alone is not a byte-for-byte
build identity: the immutable application-image digest produced by the release
workflow, its SBOM, signature, and source SHA are the authoritative release
record. A candidate is built once and promoted by digest without rebuilding.

## Hardened infrastructure runtimes

The official PostgreSQL 17.11 image is retained as the compatibility base, but
`postgres/Dockerfile` upgrades all available Debian packages and replaces the
inherited gosu binary with gosu 1.19 rebuilt from its pinned upstream commit on
Go 1.26.6. The upstream `docker-entrypoint.sh`, command, data layout, and its
hard-coded privilege drop to the `postgres` account are unchanged.

`caddy/Dockerfile` rebuilds the standard Caddy v2.11.4 module set on Go 1.26.6.
It pins `golang.org/x/net` to v0.56.0, `golang.org/x/text` to v0.39.0, and
`google.golang.org/grpc` to v1.82.1, then upgrades the final Alpine packages.
The official Caddy entrypoint and filesystem contract remain inherited.

`restic/Dockerfile` verifies the official v0.19.1 source archive checksum,
rebuilds the binary on Go 1.26.6 with the same three dependency floors, and
copies it into the pinned official v0.19.1 runtime. Its entrypoint and backup
tooling remain inherited.

All six images use the same fail-closed Trivy policy: every HIGH or CRITICAL
finding with an available fix fails CI and release. There are no file, package,
CVE, or image-specific scan exceptions. Rebuilding gosu eliminates the need for
the previously considered `/usr/local/bin/gosu` waiver; adding such a waiver is
not permitted without a new reviewed risk decision.

## Trade-offs & notes

- Pinning by digest means CI and operators must pull the exact recorded digest
  (or use a trusted registry cache) before deployment.
- `scripts/pin-images.sh` does NOT rewrite files automatically — by design,
  so that a human reviewer sees the digest bump in the diff.
