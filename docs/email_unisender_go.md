# Transactional email via Unisender Go

This document explains how Progyx sends transactional email through [Unisender Go](https://godocs.unisender.ru/),
which env variables you need, and how to test the integration locally.

## What we send

The platform sends these transactional email families:

1. **Email verification** — issued at registration and on
   `POST /api/auth/resend-verification`. Link TTL is configured via
   `EMAIL_VERIFICATION_TOKEN_TTL_MINUTES` (default 1440 = 24 h).
2. **Password reset** — issued from `POST /api/auth/forgot-password`. Link TTL is
   configured via `PASSWORD_RESET_TOKEN_TTL_MINUTES` (default 30 min).
3. **Product notifications** — a unified minimal template for teacher/admin
   notifications, new teacher lessons/assignments for students, parent child
   achievements, support messages, and weekly parent progress reminders.

Both letters are one-shot links. The raw token is shown to the user only once
(inside the email link); only `sha256(token)` is persisted in `email_tokens`.

## Env variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `EMAIL_PROVIDER` | no | `unisender_go` | Provider identifier. Today only `unisender_go` is supported. |
| `UNISENDER_GO_API_KEY` | yes (prod) | — | API key from Unisender Go → Settings → API access. |
| `UNISENDER_GO_API_URL` | yes | `https://go1.unisender.ru/ru/transactional/api/v1` | Base API URL — depends on the data centre your account lives in. |
| `UNISENDER_GO_TIMEOUT_MS` | no | `15000` | HTTP timeout for Unisender Go calls. |
| `EMAIL_FROM` | yes | — | Sender address; must belong to a verified sending domain. |
| `EMAIL_FROM_NAME` | no | `Progyx` | Display name in the From header. |
| `EMAIL_REPLY_TO` | no | — | Optional Reply-To address. |
| `FRONTEND_PUBLIC_URL` | yes | falls back to `CLIENT_URL` | Public origin used to build verify/reset links. |
| `EMAIL_VERIFICATION_TOKEN_TTL_MINUTES` | no | `1440` | TTL for the verification token. |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | no | `30` | TTL for the reset token. |
| `EMAIL_DRY_RUN` | no | `false` | When true, payload is logged with a masked recipient and no HTTP call is made. Useful for CI/local. |
| `SEND_MAIL` | no | `true` | Master switch for outgoing email. When false, `send_email` returns a skipped result. |
| `SEND_NOTIFICATION_EMAILS` | no | `true` | Switch for product notification emails only; verification/reset still use `SEND_MAIL`. |
| `MESSAGE_NOTIFICATION_EMAIL_COOLDOWN_MINUTES` | no | `15` | Cooldown for chat-like email copies per recipient/thread. In-app notifications are still written. |
| `ENABLE_PARENT_WEEKLY_PROGRESS_EMAIL_THREAD` | no | `false` | Enables the in-process weekly parent progress email runner. Prefer cron in production. |
| `PARENT_WEEKLY_PROGRESS_EMAIL_WEEKDAY_UTC` | no | `1` | Weekday for the in-process runner, Monday=0. |
| `PARENT_WEEKLY_PROGRESS_EMAIL_HOUR_UTC` | no | `8` | UTC hour for the in-process runner. |
| `PASSWORD_RESET_RATE_LIMIT_*` | no | see `.env.example` | Rate-limit window/max-attempts/block for `forgot-password`. |
| `RESEND_VERIFICATION_RATE_LIMIT_*` | no | see `.env.example` | Rate-limit window/max-attempts/block for `resend-verification`. |

Secrets must be supplied via env or a Docker secret file — never commit
`.env` to git. See `.env.example` for a complete reference.

## Choosing the right `UNISENDER_GO_API_URL`

Unisender Go shards traffic by data centre. Use the host that matches your
account region (visible in the Unisender Go dashboard URL):

* RU1 → `https://go1.unisender.ru/ru/transactional/api/v1`
* RU2 → `https://go2.unisender.ru/ru/transactional/api/v1`
* USA1 → `https://go1.unisender.com/en/transactional/api/v1`
* EU1 → `https://go1.unisender.eu/en/transactional/api/v1`

The backend appends `/email/send.json` automatically.

## Setting up DKIM/SPF/DMARC

1. In Unisender Go, add and verify your sending domain (Settings → Sending domains).
2. Publish the DKIM record (`_domainkey.<your-domain>`) and the SPF record
   (`v=spf1 include:unigosrv.com ~all`) in your DNS.
3. Optional but strongly recommended: publish DMARC at
   `_dmarc.<your-domain>` with at least `v=DMARC1; p=quarantine; rua=...`.
4. Verify with `dig TXT _domainkey.your-domain` and Unisender Go's domain
   diagnostics page.

Without DKIM most providers will park the messages in Spam.

## Local testing

### Without sending real email

Set `EMAIL_DRY_RUN=true`. The backend will skip the HTTP call but still
issue a token row, so the verification/reset flow stays end-to-end testable:
copy the link from the server logs (look for the `email_dry_run` line and
the persisted `email_tokens` row).

You can also inspect the rendered HTML/plain text via:

```python
from app.services.email_service import render_notification_email, render_password_reset_email, render_verification_email
subject, html, text = render_verification_email(user, "demo-token")
```

### With a real Unisender Go account

1. Set `UNISENDER_GO_API_KEY`, `UNISENDER_GO_API_URL`, `EMAIL_FROM`,
   `EMAIL_FROM_NAME`, and `FRONTEND_PUBLIC_URL` in `.env`.
2. Run `flask --app backend/app upgrade-db` to apply migrations.
3. Register a new user (`/auth/register`).
4. Check the inbox of the registered email; the link points to
   `${FRONTEND_PUBLIC_URL}/verify-email?token=…`.
5. Open the link — backend marks `email_verified=true` and the same link is
   immediately invalidated.

## How the flows work end-to-end

### Email verification

1. `POST /api/auth/register` → backend writes `User`, issues an
   `EmailToken(purpose="email_verification")`, calls
   `send_verification_email(user, raw_token)`.
2. User clicks the link → frontend `/verify-email?token=…` calls
   `POST /api/auth/verify-email { token }`.
3. Backend hashes the token, looks it up, validates TTL/`used_at`, marks the
   token used and sets `email_verified=true` + `email_verified_at`.
4. Re-clicking the same link returns a friendly "already verified" response
   instead of an error.

### Resend verification

`POST /api/auth/resend-verification` accepts either an authenticated session
(uses `current_user.email`) or an `{ "email": "..." }` body. Anonymous
callers always see a neutral response so we don't reveal which addresses
exist. Per-subject + per-IP rate limit caps the abuse surface.

### Forgot / reset password

1. `POST /api/auth/forgot-password { email }` always returns the same
   neutral message regardless of whether the email is registered. When a
   match is found, all earlier active reset tokens for the user are
   invalidated and a fresh one is issued.
2. User clicks the link → frontend `/reset-password?token=…` calls
   `POST /api/auth/reset-password { token, new_password }`.
3. Backend validates the password against the existing strength policy,
   consumes the token (one-shot), updates `password_hash`, sets
   `password_changed_at`, bumps `session_version`, deletes all refresh
   tokens for the user, and invalidates any other reset tokens. Old JWT
   sessions therefore stop working immediately.

### Product notifications

1. A business event calls `app.services.notifications.notify_user(...)` or a
   domain-specific wrapper such as `notify_students_new_assignment`.
2. Backend writes `user_notifications`, checks `user_notification_preferences`,
   applies dedupe/cooldown rules, and calls `send_notification_email(...)`.
3. Delivery attempts are recorded in `email_notification_logs` with `sent`,
   `dry_run`, `skipped`, or `failed`.
4. Email failures are best-effort: they are logged and do not abort the
   original action such as creating a ticket or sending a message.

Weekly parent progress emails should normally run from cron:

```bash
flask --app backend/app send-weekly-parent-progress-emails
```

Use `--force` only for manual re-sends; it bypasses the weekly dedupe key.

## Switching providers

The provider call lives in `_send_via_unisender_go` inside
`backend/app/services/email_service.py`. To plug a different ESP:

1. Add `_send_via_<provider>` with the same signature.
2. Branch on `Config.EMAIL_PROVIDER` inside `send_email`.
3. Add the provider's env vars to `Config` and `.env.example`.

`send_verification_email`, `send_password_reset_email`, and
`send_notification_email` remain unchanged.
