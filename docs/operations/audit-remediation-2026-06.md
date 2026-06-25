# Security audit remediation — 2026-06

Tracks the fixes applied for the June 2026 application security audit and the
items that still require operator action (they cannot be closed by editing
source alone).

## Fixed in code (this change)

| ID | Severity | Area | Fix |
|----|----------|------|-----|
| SEC-003 | High | Docker | Added root `.dockerignore` so `.env`, `secrets/`, `.git`, and `backend/logs/` (real PII) no longer enter the backend/judge build context or get baked into the image via `COPY backend /app/backend`. |
| SEC-004 | High | Config | `SECRET_KEY` no longer falls back to the predictable `'dev-secret-key'`; an unset key now yields a per-process random value (`secrets.token_urlsafe`). Production still requires a strong explicit key. |
| SEC-005 | Medium | Deps | `Werkzeug 3.1.3 → 3.1.4` (CVE-2025-66221, `safe_join` Windows device-name DoS). |
| SEC-006 | Medium | CSRF | Frontend `lib/api.ts` now sends `X-CSRF-Token` from the cookie for unsafe methods; the `/api/[...path]` proxy forwards **only** the client header (no longer derives it from the cookie) and pins `Origin` to the app's own origin. Restores genuine double-submit instead of relying solely on `SameSite=Strict`. |
| SEC-011 | Medium | Email | All user-controlled fields (`full_name`, `email`, achievement name/description, share text) are HTML-escaped in email markup. Closes cross-user HTML/link injection (child name → parent email). Regression test added. |
| SEC-012 | Medium | CI | Added least-privilege `permissions: contents: read` to `.github/workflows/ci.yml`. |
| SEC-014 | Low | Validation | `external_url` on useful tasks is validated server-side (http/https only, length cap) and guarded again at render (`safeHttpUrl`). Blocks `javascript:`/`data:` link injection. |
| SEC-015 | Low | Docker | Backend port bound to `127.0.0.1` only (not published on all interfaces). |
| SEC-016 | Low | Docker | `backend` and `frontend` services get `no-new-privileges:true` + `cap_drop: [ALL]` (previously only the judge-runner was hardened). |
| SEC-020 | Low | Deps | Pinned `redis==5.2.1`, `fakeredis==2.36.2`; removed the drifted `frontend/bun.lock` (CI uses npm). |
| SEC-022 | Info | Logging | CR/LF stripped from the request path in the metrics log to prevent log forging. |

## Still requires operator action (NOT fixable in code here)

| ID | Severity | Action |
|----|----------|--------|
| SEC-001 | **Critical** | Upgrade **Next.js 16.2.1 → ≥16.2.6** and react/react-dom to the matching patched 19.x (CVE-2025-66478 / React2Shell RCE, actively exploited). Requires Node/npm to regenerate `package-lock.json` — not available in the audit environment, so `package.json` was intentionally left untouched to avoid a lockfile mismatch. Rotate app secrets if the app was ever exposed on 16.2.1. |
| SEC-002 | **Critical** | Rotate the secrets present in the on-disk `.env`: `SECRET_KEY`, `UNISENDER_GO_API_KEY`, `JUDGE_RUNNER_AUTH_TOKEN`, `SUPERADMIN_PASSWORD` (and confirm the historical GigaChat key rotation, S-19). `.env` is gitignored; the leak vector is the file shipped on disk. |
| SEC-008 / SEC-009 | Medium | Sandbox lateral movement: separate the judge-runner from the backend network (one-way job queue or iptables `backend→runner:8090` only) and move seccomp to a whitelist that denies `socket`/`connect`. These need validation inside a real judge container (`test_code_judge_security` + integration), so they were not patched blind. |
| SEC-019 | Low | Digest-pin all base images via `scripts/pin-images.sh` for production builds. |

## Deferred (documented, lower priority)

- **SEC-010** (CSP `style-src 'unsafe-inline'`): left as-is — Monaco editor injects `<style>` blocks at runtime, so tightening this risks breaking the code editor. Needs frontend testing.
- **SEC-013** (no refresh-token rotation): current non-rotating design with a revocation list is acceptable; rotation + reuse-detection is a follow-up enhancement.

## Verification

- Backend: `python -m unittest discover -s backend/tests -p "test_*.py"` — full suite green (200 tests at baseline; +1 regression test for SEC-011).
- Frontend (needs Node, run in CI): `npm ci && npm run build && npx tsc -p tsconfig.check.json --noEmit`. **The SEC-006 CSRF change touches the auth request path — smoke-test login / a mutation / logout after building.**
- Infra: `docker compose config` validates; `docker build` then confirm `/app/backend/logs/audit` is empty in the image.
