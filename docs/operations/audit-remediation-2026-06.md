# Security audit remediation — 2026-06

Tracks the fixes applied for the June 2026 application security audit and the
items that still require operator action (they cannot be closed by editing
source alone).

## Fixed in code (this change)

| ID | Severity | Area | Fix |
|----|----------|------|-----|
| SEC-001 | **Critical** | Deps | Upgraded **Next.js 16.2.1 → 16.2.9** and **react/react-dom 19.2.0 → 19.2.7** (React2Shell RCE CVE-2025-66478 / CVE-2025-55182 + the May 2026 batch), staying on the 16.2 line. `npm audit` now reports **0 vulnerabilities**; `npm run build` + `tsc --noEmit` pass. |
| SEC-003 | High | Docker | Added root `.dockerignore` so `.env`, `secrets/`, `.git`, and `backend/logs/` (real PII) no longer enter the backend/judge build context or get baked into the image via `COPY backend /app/backend`. |
| SEC-004 | High | Config | `SECRET_KEY` no longer falls back to the predictable `'dev-secret-key'`; an unset key now yields a per-process random value (`secrets.token_urlsafe`). Production still requires a strong explicit key. |
| SEC-005 | Medium | Deps | `Werkzeug 3.1.3 → 3.1.4` (CVE-2025-66221, `safe_join` Windows device-name DoS). |
| SEC-006 | Medium | CSRF | Frontend `lib/api.ts` now sends `X-CSRF-Token` from the cookie for unsafe methods; the `/api/[...path]` proxy forwards **only** the client header (no longer derives it from the cookie) and pins `Origin` to the app's own origin. Restores genuine double-submit instead of relying solely on `SameSite=Strict`. |
| SEC-011 | Medium | Email | All user-controlled fields (`full_name`, `email`, achievement name/description, share text) are HTML-escaped in email markup. Closes cross-user HTML/link injection (child name → parent email). Regression test added. |
| SEC-012 | Medium | CI | Added least-privilege `permissions: contents: read` to `.github/workflows/ci.yml`. |
| SEC-014 | Low | Validation | `external_url` on useful tasks is validated server-side (http/https only, length cap) and guarded again at render (`safeHttpUrl`). Blocks `javascript:`/`data:` link injection. |
| SEC-015 | Low | Docker | Backend port bound to `127.0.0.1` only (not published on all interfaces). |
| SEC-016 | Low | Docker | `backend` and `frontend` services get `no-new-privileges:true` + `cap_drop: [ALL]` (previously only the judge-runner was hardened). |
| SEC-019 | Low | Docker | All base images digest-pinned to their current multi-arch manifest (`python:3.12-slim`, `node:22-alpine`, `postgres:17`, `redis:7-alpine`) across the three Dockerfiles, `docker-compose.yml`, and CI services. Reproducible/tamper-evident builds; refresh via `scripts/pin-images.sh`. Validated with `docker compose config` + a backend/judge build. |
| SEC-020 | Low | Deps | Pinned `redis==5.2.1`, `fakeredis==2.36.2`; removed the drifted `frontend/bun.lock` (CI uses npm). Pinned `next`/`react`/`react-dom` to exact versions and added `overrides` forcing `dompurify@^3.4.11` + `postcss@^8.5.15` — frontend tree now has **0 npm audit findings**. |
| SEC-008 / SEC-009 | Medium | Sandbox | Per-execution seccomp BPF filter in the judge-runner `preexec_fn` denies `connect(2)` for the forked user-code child only (`SECCOMP_RET_ERRNO`/EPERM, never KILL; x86_64; best-effort/fail-open). Closes the lateral-movement path to `backend:8000` over `judge_net` (by IP → EPERM; by hostname → DNS also fails) and neuters the `/proc` token-leak (code can no longer connect out to use it). Runner process + healthcheck unaffected. **Confirmed both the vuln and the fix against a running stack.** |
| SEC-022 | Info | Logging | CR/LF stripped from the request path in the metrics log to prevent log forging. |

## Still requires operator action (NOT fixable in code here)

| ID | Severity | Action |
|----|----------|--------|
| SEC-002 | **Critical** | Rotate the secrets present in the on-disk `.env`: `SECRET_KEY`, `UNISENDER_GO_API_KEY`, `JUDGE_RUNNER_AUTH_TOKEN`, `SUPERADMIN_PASSWORD` (and confirm the historical GigaChat key rotation, S-19). `.env` is gitignored; the leak vector is the file shipped on disk. **This is the only remaining must-do item.** |

## Deferred (documented, lower priority)

- **SEC-010** (CSP `style-src 'unsafe-inline'`): left as-is — Monaco editor injects `<style>` blocks at runtime, so tightening this risks breaking the code editor. Needs frontend testing.
- **SEC-013** (no refresh-token rotation): current non-rotating design with a revocation list is acceptable; rotation + reuse-detection is a follow-up enhancement.
- **SEC-008/009 (residual hardening)**: the exploitable lateral-movement path is closed (see above). A container-level seccomp *whitelist* (vs. the current allow-by-default denylist) and a one-way job queue / `backend→runner:8090`-only network policy remain recommended defence-in-depth, but are no longer required to close the finding.
- **SEC-007** (rate-limiting keyed on the proxy IP): a correct fix needs a trusted edge reverse proxy that injects the real client IP, the Next proxy forwarding `X-Forwarded-For`, and `TRUST_PROXY=true`. Forwarding a client-supplied `X-Forwarded-For` *without* a trusted edge would let clients spoof their IP and **evade** per-IP limits — strictly worse than today — so this is intentionally deferred to a deployment-topology decision rather than patched blind.
- **Low/Info backlog** (from the audit, not addressed in this change): SEC-017 (self-graded assignment auto-score, teacher review is the backstop), SEC-018 (regular admins control bug-hunter XP — confirm product intent), SEC-021 (no throttle on bug-reports), SEC-025 (CI `actions/*` pinned to tags, not commit SHAs).

## Verification

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` — full suite green (200 tests at baseline; +1 regression test for SEC-011).
- Frontend (verified locally on Node 22.23.1): `npm install` → `npm audit` reports **0 vulnerabilities**; `npm run build` and `npx tsc -p tsconfig.check.json --noEmit` both pass. **The SEC-006 CSRF change touches the auth request path — still smoke-test login / a mutation / logout in a running environment before deploy.**
- Infra: `docker compose config` validates; `docker build` then confirm `/app/backend/logs/audit` is empty in the image.
