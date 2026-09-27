# ruff: noqa: E402

import sys
import threading
import time
import os
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlparse

import redis

from flask import Flask, abort, g, has_request_context, request, send_from_directory
from flask.testing import FlaskClient
from flask_cors import CORS
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.datastructures import Headers
from werkzeug.exceptions import NotFound, RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .api.admin import admin_bp
from .api.auth import auth_bp
from .api.cosmetics import cosmetics_bp
from .api.messaging import messaging_bp
from .api.notifications import notifications_bp
from .api.staff_messaging import staff_messaging_bp
from .api.parent_cabinet import parent_bp
from .api.student import student_bp
from .api.teacher import teacher_bp
from .api.useful import useful_bp
from .api.support import support_bp
from .cli import register_commands
from .core.config import Config, resolve_jwt_signing_keys, resolve_redis_password
from .core.db import db
from .core.security import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    SAFE_HTTP_METHODS,
    access_token_from_request,
    decode_token,
    request_origin_allowed,
    request_uses_cookie_auth,
    verify_csrf_token,
)

SPRITE_DIR = Path(__file__).resolve().parent.parent / "sprite"
_MEDIA_ENV = os.environ.get("MEDIA_DIR")
MEDIA_DIR = Path(_MEDIA_ENV) if _MEDIA_ENV and Path(_MEDIA_ENV).is_dir() else PROJECT_ROOT / "media"
COMMON_SECRET_KEY_PLACEHOLDERS = (
    "change-me",
    "replace-me",
    "your-secret",
    "dev-secret",
    "super-secret-key",
    "example",
    "todo",
    # Reject example-file leftovers that pass length but encode obvious dev defaults.
    "devpostgres",
    "devredis",
    "devjudge",
    "localonly",
    "localdev",
    "passphrase",
)
PUBLIC_UNSAFE_API_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
}


def _normalized_path(path: str) -> str:
    normalized = (path or "").strip()
    if not normalized:
        return "/"
    normalized = normalized.rstrip("/")
    return normalized or "/"


def _is_public_unsafe_api_path(path: str) -> bool:
    return _normalized_path(path) in PUBLIC_UNSAFE_API_PATHS


def _contains_placeholder_secret_fragment(value: str) -> bool:
    normalized = value.lower()
    return any(fragment in normalized for fragment in COMMON_SECRET_KEY_PLACEHOLDERS)


def _is_trivially_low_entropy_secret(value: str) -> bool:
    if not value:
        return True
    if len(set(value)) == 1:
        return True
    if len(value) < 40 and (value.isdigit() or (value.isalpha() and value.islower())):
        return True
    return False


def _validate_secret_material(name: str, value: str, min_length: int = 32) -> None:
    if len(value) < min_length:
        raise RuntimeError(f"Set a strong {name} before running in production mode.")
    if _contains_placeholder_secret_fragment(value):
        raise RuntimeError(f"Set a strong {name} before running in production mode.")
    if _is_trivially_low_entropy_secret(value):
        raise RuntimeError(f"Set a strong {name} before running in production mode.")


def _validate_jwt_keyring(app: Flask, secret_key: str) -> None:
    key_id = str(app.config.get("JWT_SIGNING_KEY_ID") or "").strip()
    if not key_id or any(char.isspace() for char in key_id) or len(key_id) > 64:
        raise RuntimeError("JWT_SIGNING_KEY_ID must be a non-empty, no-whitespace string up to 64 chars.")
    try:
        keyring = resolve_jwt_signing_keys(
            secret_key,
            key_id,
            app.config.get("JWT_SIGNING_KEYS"),
        )
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    if key_id not in keyring:
        raise RuntimeError("JWT_SIGNING_KEY_ID must reference an entry in JWT_SIGNING_KEYS.")
    if app.config["IS_PRODUCTION"]:
        for jwt_key_id, jwt_key in keyring.items():
            _validate_secret_material(f"JWT signing key '{jwt_key_id}'", jwt_key)


def _validate_postgres_password(app: Flask) -> None:
    database_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    parsed = urlparse(database_uri)
    if not parsed.scheme.startswith("postgresql"):
        return
    password = parsed.password or ""
    if password in {"", "codequest", "postgres", "password"} or len(password) < 16:
        raise RuntimeError("Set a strong PostgreSQL password before running in production mode.")
    if _contains_placeholder_secret_fragment(password):
        raise RuntimeError(
            "PostgreSQL password must not contain placeholder fragments (Dev/Local/example/etc) in production."
        )


def _validate_email_address(name: str, value: str) -> None:
    local_part, separator, domain = value.strip().partition("@")
    if (
        not separator
        or not local_part
        or not domain
        or "@" in domain
        or any(char.isspace() for char in value)
    ):
        raise RuntimeError(f"{name} must be a valid email address when SEND_MAIL=true in production.")


def _validate_https_url(name: str, value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.fragment)
    ):
        raise RuntimeError(f"{name} must be an absolute HTTPS URL when SEND_MAIL=true in production.")


def _validate_https_origin(name: str, value: str) -> None:
    if "," in value:
        raise RuntimeError(f"{name} must contain exactly one HTTPS origin in production mode.")
    parsed = urlparse(value)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"{name} must contain a valid HTTPS origin in production mode.") from exc
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or bool(parsed.path)
        or bool(parsed.params)
        or bool(parsed.query)
        or bool(parsed.fragment)
    ):
        raise RuntimeError(f"{name} must be an absolute HTTPS origin without a path in production mode.")


def _validate_production_email_config(app: Flask) -> None:
    if not app.config["IS_PRODUCTION"] or not app.config.get("SEND_MAIL"):
        return
    if app.config.get("EMAIL_DRY_RUN"):
        raise RuntimeError("EMAIL_DRY_RUN must be disabled when SEND_MAIL=true in production.")
    provider = str(app.config.get("EMAIL_PROVIDER") or "").strip().lower()
    if provider != "unisender_go":
        raise RuntimeError("EMAIL_PROVIDER must be 'unisender_go' when SEND_MAIL=true in production.")
    api_key = str(app.config.get("UNISENDER_GO_API_KEY") or "").strip()
    if not api_key or _contains_placeholder_secret_fragment(api_key):
        raise RuntimeError("Set a non-placeholder UNISENDER_GO_API_KEY when SEND_MAIL=true in production.")
    _validate_https_url(
        "UNISENDER_GO_API_URL",
        str(app.config.get("UNISENDER_GO_API_URL") or "").strip(),
    )
    _validate_email_address("EMAIL_FROM", str(app.config.get("EMAIL_FROM") or ""))
    reply_to = str(app.config.get("EMAIL_REPLY_TO") or "").strip()
    if reply_to:
        _validate_email_address("EMAIL_REPLY_TO", reply_to)
    frontend_url = str(app.config.get("FRONTEND_PUBLIC_URL") or "").strip()
    _validate_https_origin("FRONTEND_PUBLIC_URL", frontend_url)


class _CSRFAwareFlaskClient(FlaskClient):
    def open(self, *args, **kwargs):  # noqa: ANN002, ANN003
        method = str(kwargs.get("method") or "").upper()
        path = kwargs.get("path")
        if path is None and args and isinstance(args[0], str):
            path = args[0]

        if (
            self.application.testing
            and self.application.config.get("AUTO_TEST_CSRF_HEADER", True)
            and method in {"POST", "PUT", "PATCH", "DELETE"}
            and isinstance(path, str)
            and path.startswith("/api/")
            and not _is_public_unsafe_api_path(path)
        ):
            headers = Headers(kwargs.get("headers") or {})
            if CSRF_HEADER_NAME not in headers:
                csrf_cookie = self.get_cookie(CSRF_COOKIE_NAME)
                csrf_token = csrf_cookie.value if csrf_cookie else ""
                if csrf_token:
                    headers[CSRF_HEADER_NAME] = csrf_token
                    kwargs["headers"] = headers

        return super().open(*args, **kwargs)


def _redis_production_config_ok(url: str, password: str | None) -> tuple[bool, str | None]:
    lowered = url.strip().lower()
    if any(
        fragment in lowered
        for fragment in (
            'change-me',
            'replace-me',
            'your-redis',
            'example',
            'placeholder',
            'todo',
        )
    ):
        return False, 'REDIS_URL looks like a placeholder.'
    parsed = urlparse(url)
    if parsed.scheme not in {'redis', 'rediss'}:
        return False, 'REDIS_URL must use redis:// or rediss:// scheme.'
    if parsed.scheme == 'rediss':
        return False, 'REDIS_URL must use redis:// in this deployment (TLS URLs are not enabled for Redis yet).'
    has_auth = bool(parsed.password) or bool(password and password.strip())
    if not has_auth:
        return False, 'REDIS_URL must include credentials or set REDIS_PASSWORD / REDIS_PASSWORD_FILE.'
    return True, None


def _validate_runtime_config(app: Flask) -> None:
    secret_key = (app.config.get("SECRET_KEY") or "").strip()
    if app.config["IS_PRODUCTION"]:
        _validate_secret_material("SECRET_KEY", secret_key)
    _validate_jwt_keyring(app, secret_key)
    if app.config["IS_PRODUCTION"] and not app.config.get("SESSION_COOKIE_SECURE", True):
        raise RuntimeError("SESSION_COOKIE_SECURE must stay enabled in production mode.")
    if app.config["IS_PRODUCTION"] and str(app.config.get("SESSION_COOKIE_SAMESITE") or "").lower() != "strict":
        raise RuntimeError("SESSION_COOKIE_SAMESITE must be Strict in production mode.")
    if app.config["IS_PRODUCTION"]:
        client_url = str(app.config.get("CLIENT_URL") or "").strip()
        if not client_url:
            raise RuntimeError("Set CLIENT_URL in production mode.")
        _validate_https_origin("CLIENT_URL", client_url)
    legal_documents_version = str(app.config.get("LEGAL_DOCUMENTS_VERSION") or "").strip()
    if app.config["IS_PRODUCTION"] and (
        not legal_documents_version
        or len(legal_documents_version) > 64
        or legal_documents_version.lower() in {
            "dev",
            "development",
            "development-v1",
            "latest",
            "current",
            "unset",
        }
        or _contains_placeholder_secret_fragment(legal_documents_version)
    ):
        raise RuntimeError(
            "Set a non-placeholder LEGAL_DOCUMENTS_VERSION before running in production mode."
        )
    max_content_length = app.config.get("MAX_CONTENT_LENGTH")
    if (
        not isinstance(max_content_length, int)
        or isinstance(max_content_length, bool)
        or max_content_length <= 0
        or max_content_length > 64 * 1024 * 1024
    ):
        raise RuntimeError("MAX_CONTENT_LENGTH must be an integer between 1 and 67108864 bytes.")
    _validate_production_email_config(app)
    if app.config["IS_PRODUCTION"] and (app.config.get("CODE_JUDGE_RUNNER_URL") or "").strip():
        runner_token = (app.config.get("CODE_JUDGE_RUNNER_TOKEN") or "").strip()
        runner_token_lower = runner_token.lower()
        if (
            not runner_token_lower
            or len(runner_token) < 32
            or any(marker in runner_token_lower for marker in ("replace", "change-me", "example", "placeholder", "local-dev", "test-token"))
        ):
            raise RuntimeError("Set a strong CODE_JUDGE_RUNNER_TOKEN before enabling the code judge runner in production.")
    if app.config["IS_PRODUCTION"] and app.config.get("SUPERADMIN_BOOTSTRAP"):
        from .core.security import ADMIN_PASSWORD_MIN_LENGTH, validate_password

        superadmin_email = (app.config.get("SUPERADMIN_EMAIL") or "").strip().lower()
        superadmin_password = app.config.get("SUPERADMIN_PASSWORD") or ""
        if not superadmin_email or not superadmin_password:
            raise RuntimeError(
                "SUPERADMIN_BOOTSTRAP requires explicit SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD in production mode."
            )
        password_error = validate_password(
            superadmin_password,
            minimum_length=ADMIN_PASSWORD_MIN_LENGTH,
        )
        if password_error:
            raise RuntimeError(f"SUPERADMIN_PASSWORD is not secure enough: {password_error}")
    if app.config["IS_PRODUCTION"]:
        _validate_postgres_password(app)
        redis_url = (app.config.get("REDIS_URL") or "").strip()
        if not redis_url:
            raise RuntimeError("Set REDIS_URL before running in production mode.")
        redis_password = (resolve_redis_password() or "").strip()
        if len(redis_password) < 24:
            raise RuntimeError(
                "Set a strong Redis password (REDIS_PASSWORD or REDIS_PASSWORD_FILE, min 24 characters) for production."
            )
        if _contains_placeholder_secret_fragment(redis_password):
            raise RuntimeError("Redis password must not contain placeholder fragments in production mode.")
        if _is_trivially_low_entropy_secret(redis_password):
            raise RuntimeError("Redis password is too weak for production mode.")
        ok, redis_err = _redis_production_config_ok(redis_url, redis_password)
        if not ok:
            raise RuntimeError(redis_err or "Invalid REDIS_URL for production mode.")


def _database_ready() -> bool:
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except (OSError, RuntimeError, SQLAlchemyError):
        return False


def _redis_ready(app: Flask) -> tuple[bool | None, bool]:
    redis_url = str(app.config.get("REDIS_URL") or "").strip()
    redis_required = bool(app.config.get("READINESS_REQUIRE_REDIS"))
    redis_checked = redis_required or bool(redis_url)
    if not redis_checked:
        return None, False
    if not redis_url:
        return False, True
    from .core.redis_client import redis_ping_with_timeout_ms

    return bool(redis_ping_with_timeout_ms()), True


def _probe_judge_health(runner_url: str, timeout_ms: int) -> bool:
    parsed = urlparse(runner_url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return False
    health_url = parsed._replace(path="/health", params="", query="", fragment="").geturl()
    health_request = urllib_request.Request(
        health_url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    timeout_seconds = max(min(int(timeout_ms), 5000), 100) / 1000.0
    try:
        with urllib_request.urlopen(health_request, timeout=timeout_seconds) as response:
            if int(getattr(response, "status", 0) or 0) != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
    except (
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        UnicodeError,
        urllib_error.HTTPError,
        urllib_error.URLError,
    ):
        return False
    return isinstance(payload, dict) and payload.get("status") == "ok"


def _judge_ready(app: Flask) -> tuple[bool | None, bool]:
    runner_url = str(app.config.get("CODE_JUDGE_RUNNER_URL") or "").strip()
    judge_required = bool(app.config.get("READINESS_REQUIRE_JUDGE"))
    judge_checked = judge_required or bool(runner_url)
    if not judge_checked:
        return None, False
    if not runner_url:
        return False, True
    timeout_ms = int(app.config.get("READINESS_JUDGE_TIMEOUT_MS") or 500)
    return _probe_judge_health(runner_url, timeout_ms), True


def _readiness_payload(app: Flask, *, legacy_health: bool = False) -> tuple[dict, int]:
    database_ok = _database_ready()
    redis_ok, redis_checked = _redis_ready(app)
    judge_ok, judge_checked = _judge_ready(app)
    ready = (
        database_ok
        and (not redis_checked or redis_ok is True)
        and (not judge_checked or judge_ok is True)
    )
    checks = {"database": database_ok, "redis": redis_ok, "judge": judge_ok}
    payload = {
        "status": "ok" if ready and legacy_health else ("ready" if ready else "not_ready"),
        "checks": checks,
        # Keep the historic top-level fields useful for existing monitors.
        "database": database_ok,
    }
    if redis_checked:
        payload["redis"] = redis_ok
    if judge_checked:
        payload["judge"] = judge_ok
    return payload, 200 if ready else 503


_MAINT_FLAG_LOCK = threading.Lock()
_MAINT_FLAG_UNTIL = 0.0
_MAINT_FLAG_VALUE = False


def _maintenance_flag_active(app: Flask) -> bool:
    global _MAINT_FLAG_UNTIL, _MAINT_FLAG_VALUE
    now = time.monotonic()
    with _MAINT_FLAG_LOCK:
        if now < _MAINT_FLAG_UNTIL:
            return _MAINT_FLAG_VALUE
    active = False
    try:
        from .core.config import Config as _Cfg
        from .core.redis_client import get_redis, redis_key

        client = get_redis(_Cfg.REDIS_DB_LEADERBOARD)
        if client is not None:
            raw = client.get(redis_key("flags", "maintenance"))
            active = str(raw or "").strip().lower() in {"1", "true", "yes", "on"}
    except (OSError, TypeError, ValueError, redis.RedisError):
        active = False
    with _MAINT_FLAG_LOCK:
        _MAINT_FLAG_VALUE = active
        _MAINT_FLAG_UNTIL = now + 5.0
    return active


def _register_request_metrics(app: Flask) -> None:
    if not app.config.get("METRICS_DEBUG", False):
        return

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        if has_request_context():
            g._db_query_count = getattr(g, "_db_query_count", 0) + 1

    with app.app_context():
        engine = db.engine
        if not getattr(engine, "_codequest_metrics_registered", False):
            event.listen(engine, "before_cursor_execute", before_cursor_execute)
            engine._codequest_metrics_registered = True

    @app.before_request
    def start_request_timer():
        g._request_started_at = time.perf_counter()
        g._db_query_count = 0

    @app.after_request
    def attach_request_metrics(response):
        started_at = getattr(g, "_request_started_at", None)
        duration_ms = int((time.perf_counter() - started_at) * 1000) if started_at else 0
        query_count = getattr(g, "_db_query_count", 0)
        response.headers.setdefault("X-Request-Duration-Ms", str(duration_ms))
        response.headers.setdefault("X-DB-Query-Count", str(query_count))
        app.logger.info(
            "request_metrics method=%s path=%s status=%s duration_ms=%s query_count=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            query_count,
        )
        return response


def create_app() -> Flask:
    started_at = time.perf_counter()
    app = Flask(__name__)
    app.test_client_class = _CSRFAwareFlaskClient
    app.config.from_object(Config)
    _validate_runtime_config(app)
    if app.config.get("TRUST_PROXY", False):
        # Enable this only when running behind a trusted reverse proxy.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=0)

    allowed_origins = [
        origin.strip()
        for origin in (app.config.get("CLIENT_URL") or "").split(",")
        if origin.strip()
    ]
    if not allowed_origins:
        allowed_origins = ["http://localhost:3000"]
    db.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
    )

    with app.app_context():
        from . import models  # noqa: F401

    register_commands(app)
    _register_request_metrics(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(student_bp, url_prefix="/api")
    app.register_blueprint(cosmetics_bp, url_prefix="/api")
    app.register_blueprint(parent_bp, url_prefix="/api/parent")
    app.register_blueprint(teacher_bp, url_prefix="/api/teacher")
    app.register_blueprint(messaging_bp, url_prefix="/api/messaging")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(staff_messaging_bp, url_prefix="/api/staff-messaging")
    app.register_blueprint(support_bp, url_prefix="/api/support")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(useful_bp, url_prefix="/api/useful")

    @app.errorhandler(RequestEntityTooLarge)
    def request_entity_too_large(_error: RequestEntityTooLarge):
        return {
            "message": "Request body exceeds the configured size limit.",
            "code": "request_too_large",
            "max_bytes": app.config["MAX_CONTENT_LENGTH"],
        }, 413

    @app.get("/api/live")
    def liveness():
        return {"status": "ok"}

    @app.get("/api/ready")
    def readiness():
        return _readiness_payload(app)

    @app.get("/api/health")
    def health():
        # Backward-compatible path used by existing deployments. Unlike the old
        # implementation, it now reports dependency failure via a non-2xx status.
        return _readiness_payload(app, legacy_health=True)

    @app.before_request
    def enforce_maintenance_mode():
        if request.method in SAFE_HTTP_METHODS:
            return None
        path = request.path or ""
        if path.startswith(("/api/health", "/api/live", "/api/ready")):
            return None
        if not _maintenance_flag_active(app):
            return None
        try:
            token = access_token_from_request()
            if token:
                payload = decode_token(token)
                role = str(payload.get("role") or "").lower()
                if role in {"admin", "superadmin"}:
                    return None
        except Exception:
            pass
        return {"message": "Платформа в режиме обслуживания. Запись временно недоступна."}, 503

    @app.before_request
    def enforce_origin_for_unsafe_api_requests():
        if request.method in SAFE_HTTP_METHODS:
            return None
        if not request.path.startswith("/api/"):
            return None
        if request_origin_allowed():
            return None
        return {"message": "Недопустимый origin для этого запроса."}, 403

    @app.before_request
    def enforce_csrf_for_cookie_authenticated_unsafe_api_requests():
        if request.method in SAFE_HTTP_METHODS:
            return None
        if not request.path.startswith("/api/"):
            return None
        if _is_public_unsafe_api_path(request.path):
            return None
        if not request_uses_cookie_auth():
            return None
        if verify_csrf_token():
            return None
        return {"message": "CSRF token missing or invalid.", "code": "csrf_invalid"}, 403

    # Defense-in-depth: send_from_directory blocks `..` traversal, but we additionally
    # restrict file extensions so mis-placed files (e.g. .html, raw .svg with embedded scripts)
    # cannot be served as media even if an operator copies them into the media directories.
    _ALLOWED_MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    def _ensure_allowed_media_extension(filename: str) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_MEDIA_EXTENSIONS:
            abort(404)

    @app.get("/api/mascot/<path:filename>")
    def mascot_sprite(filename: str):
        _ensure_allowed_media_extension(filename)
        return send_from_directory(SPRITE_DIR, filename)

    @app.get("/api/media/avatars/<path:filename>")
    def media_avatar(filename: str):
        _ensure_allowed_media_extension(filename)
        try:
            return send_from_directory(MEDIA_DIR / "avatars", filename)
        except NotFound:
            return send_from_directory(PROJECT_ROOT / "media" / "avatars", filename)

    @app.get("/api/media/frames/<path:filename>")
    def media_frame(filename: str):
        _ensure_allowed_media_extension(filename)
        try:
            return send_from_directory(MEDIA_DIR / "frames", filename)
        except NotFound:
            return send_from_directory(PROJECT_ROOT / "media" / "frames", filename)

    # Assignment cover images allow .svg in addition to raster formats: SVG placeholders
    # are generated server-side (no user input substituted into <text>), and our global
    # CSP for /api/* responses (`default-src 'none'`) blocks any inline script execution
    # if a malformed SVG sneaks in. Avatars/frames keep the stricter raster-only whitelist.
    _ALLOWED_ASSIGNMENT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

    def _ensure_allowed_assignment_image_extension(filename: str) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in _ALLOWED_ASSIGNMENT_IMAGE_EXTENSIONS:
            abort(404)

    @app.get("/api/media/assignment-images/<path:filename>")
    def media_assignment_image(filename: str):
        _ensure_allowed_assignment_image_extension(filename)
        return send_from_directory(MEDIA_DIR / "assignment-images", filename)

    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if app.config.get("IS_PRODUCTION"):
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        response.headers.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        return response

    if app.config.get("METRICS_DEBUG", False):
        app.logger.info("create_app completed in %sms", int((time.perf_counter() - started_at) * 1000))

    if not app.config.get("TESTING") and app.config.get("ENABLE_AUDIT_LOG_DAILY_EXPORT_THREAD"):
        _start_audit_log_export_thread(app)
    if not app.config.get("TESTING") and app.config.get("ENABLE_PARENT_WEEKLY_PROGRESS_EMAIL_THREAD"):
        _start_parent_weekly_progress_email_thread(app)

    from .services.site_activity_log import register_site_activity_logging

    register_site_activity_logging(app)

    return app


def _start_audit_log_export_thread(app: Flask) -> None:
    """In-process daily export. Disable on multi-worker deployments; use `flask export-audit-logs` + cron."""

    def run_loop() -> None:
        while True:
            try:
                hour_utc = int(app.config.get("AUDIT_LOG_DAILY_EXPORT_HOUR_UTC", 3))
                hour_utc = max(0, min(23, hour_utc))
                now = datetime.now(UTC)
                target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                sleep_s = (target - now).total_seconds()
                time.sleep(sleep_s)
                with app.app_context():
                    from .services.audit_log_archive import run_daily_admin_log_exports

                    result = run_daily_admin_log_exports()
                    app.logger.info("daily_admin_log_export %s", result)
            except Exception:  # noqa: BLE001
                app.logger.exception("daily_admin_log_export loop failed")
                time.sleep(60.0)

    threading.Thread(target=run_loop, name="audit-log-export", daemon=True).start()


def _start_parent_weekly_progress_email_thread(app: Flask) -> None:
    """In-process weekly parent progress email runner. Prefer external cron in multi-worker deployments."""

    def run_loop() -> None:
        while True:
            try:
                weekday_utc = int(app.config.get("PARENT_WEEKLY_PROGRESS_EMAIL_WEEKDAY_UTC", 1))
                weekday_utc = max(0, min(6, weekday_utc))
                hour_utc = int(app.config.get("PARENT_WEEKLY_PROGRESS_EMAIL_HOUR_UTC", 8))
                hour_utc = max(0, min(23, hour_utc))
                now = datetime.now(UTC)
                days_ahead = (weekday_utc - now.weekday()) % 7
                target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
                if target <= now:
                    target += timedelta(days=7)
                time.sleep((target - now).total_seconds())
                with app.app_context():
                    from .services.notifications import run_weekly_parent_progress_reminders

                    result = run_weekly_parent_progress_reminders()
                    db.session.commit()
                    app.logger.info("parent_weekly_progress_email %s", result)
            except Exception:  # noqa: BLE001
                app.logger.exception("parent_weekly_progress_email loop failed")
                time.sleep(60.0)

    threading.Thread(target=run_loop, name="parent-weekly-progress-email", daemon=True).start()
