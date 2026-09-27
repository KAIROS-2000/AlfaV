from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import click
from flask import Flask, current_app
from flask.cli import with_appcontext
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .core.db import db
from .core.migrations import upgrade_database


FIRST_SUPERADMIN_ADVISORY_LOCK_ID = 764_891_273_012_345_679
PROVISION_SUPERADMIN_EMAIL_ENV = 'PROVISION_SUPERADMIN_EMAIL'
PROVISION_SUPERADMIN_NAME_ENV = 'PROVISION_SUPERADMIN_NAME'
PROVISION_SUPERADMIN_PASSWORD_FILE_ENV = 'PROVISION_SUPERADMIN_PASSWORD_FILE'
MAX_PROVISION_PASSWORD_FILE_BYTES = 4096


def _ensure_models_loaded() -> None:
    from . import models  # noqa: F401


def _provision_superadmin_credentials() -> tuple[str, str, str]:
    from .api.auth import is_valid_email
    from .core.security import ADMIN_PASSWORD_MIN_LENGTH, validate_password

    email = (os.getenv(PROVISION_SUPERADMIN_EMAIL_ENV) or '').strip().lower()
    name = (os.getenv(PROVISION_SUPERADMIN_NAME_ENV) or '').strip()
    password_file_raw = (os.getenv(PROVISION_SUPERADMIN_PASSWORD_FILE_ENV) or '').strip()
    if not email or not name or not password_file_raw:
        raise click.ClickException(
            'Set PROVISION_SUPERADMIN_EMAIL, PROVISION_SUPERADMIN_NAME, and '
            'PROVISION_SUPERADMIN_PASSWORD_FILE.'
        )
    if not is_valid_email(email):
        raise click.ClickException('PROVISION_SUPERADMIN_EMAIL must be a valid email address.')
    if len(name) > 120:
        raise click.ClickException('PROVISION_SUPERADMIN_NAME must be at most 120 characters.')

    password_file = Path(password_file_raw).expanduser()
    try:
        if not password_file.is_file():
            raise click.ClickException('PROVISION_SUPERADMIN_PASSWORD_FILE must reference a readable file.')
        if password_file.stat().st_size > MAX_PROVISION_PASSWORD_FILE_BYTES:
            raise click.ClickException('PROVISION_SUPERADMIN_PASSWORD_FILE is unexpectedly large.')
        password = password_file.read_text(encoding='utf-8').replace('\r', '').strip()
    except click.ClickException:
        raise
    except (OSError, UnicodeError) as exc:
        raise click.ClickException('Unable to read PROVISION_SUPERADMIN_PASSWORD_FILE.') from exc
    if '\n' in password:
        raise click.ClickException('PROVISION_SUPERADMIN_PASSWORD_FILE must contain exactly one line.')
    password_error = validate_password(password, minimum_length=ADMIN_PASSWORD_MIN_LENGTH)
    if password_error:
        raise click.ClickException(f'Provisioning password is not secure enough: {password_error}')
    return email, name, password


def _provision_first_superadmin() -> None:
    from .core.security import hash_password
    from .models.user import AdminAuditLog, User, UserRole

    email, name, password = _provision_superadmin_credentials()
    _ensure_models_loaded()
    upgrade_database()
    now = datetime.now(UTC)
    try:
        if db.engine.dialect.name == 'postgresql':
            db.session.execute(
                text('SELECT pg_advisory_xact_lock(:lock_id)'),
                {'lock_id': FIRST_SUPERADMIN_ADVISORY_LOCK_ID},
            )
        if User.query.filter_by(role=UserRole.SUPERADMIN).first() is not None:
            raise click.ClickException('A superadmin already exists; refusing to provision another one.')
        if User.query.filter(User.email == email).first() is not None:
            raise click.ClickException('An account with the provisioning email already exists.')

        user = User(
            full_name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.SUPERADMIN,
            age_group='adult',
            is_active=True,
            email_verified=True,
            email_verified_at=now,
            password_changed_at=now,
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(
            AdminAuditLog(
                actor_user_id=user.id,
                actor_role=UserRole.SUPERADMIN.value,
                action='initial_superadmin_provisioned',
                entity_type='user',
                entity_id=user.id,
                entity_label=user.email,
                details_json={
                    'actor_name': user.full_name,
                    'actor_email': user.email,
                    'provisioning_method': 'cli',
                    'credential_source': 'password_file',
                },
            )
        )
        db.session.commit()
    except click.ClickException:
        db.session.rollback()
        raise
    except IntegrityError as exc:
        db.session.rollback()
        raise click.ClickException('Superadmin provisioning conflicted with an existing account.') from exc
    except Exception:
        db.session.rollback()
        raise


def _run_judge_smoke() -> None:
    from .core.code_judge import CodeJudgeError, _post_to_runner

    smoke_cases = (
        (
            'python',
            'print(input())',
        ),
        (
            'javascript',
            (
                "process.stdin.setEncoding('utf8');\n"
                "let data = '';\n"
                "process.stdin.on('data', chunk => data += chunk);\n"
                "process.stdin.on('end', () => console.log(data.trim()));\n"
            ),
        ),
    )
    for language, source in smoke_cases:
        try:
            report = _post_to_runner(
                {
                    'language': language,
                    'code': source,
                    'tests': [
                        {
                            'label': 'production-smoke-echo',
                            'input': 'judge-smoke-value',
                            'expected': 'judge-smoke-value',
                        }
                    ],
                    # This is a connectivity/runtime canary, not a student
                    # performance limit. Leave headroom for a cold container
                    # and first interpreter startup on a constrained host.
                    'time_limit_ms': 5000,
                    'memory_limit_mb': 128,
                    'max_output_chars': 1024,
                }
            )
        except CodeJudgeError as exc:
            raise click.ClickException(f'Judge smoke failed for {language}.') from exc
        if (
            report.get('passed') is not True
            or report.get('tests_passed') != 1
            or report.get('tests_total') != 1
        ):
            raise click.ClickException(f'Judge smoke failed for {language}.')


def register_commands(app: Flask) -> None:
    @app.cli.command('judge-smoke')
    @with_appcontext
    def judge_smoke_command() -> None:
        """Verify configured judge execution for supported production languages."""

        _run_judge_smoke()
        click.echo('Judge smoke passed for Python and JavaScript.')

    @app.cli.command('provision-first-superadmin')
    @with_appcontext
    def provision_first_superadmin_command() -> None:
        """Provision the first superadmin from explicit non-interactive credentials."""

        _provision_first_superadmin()
        click.echo('Initial superadmin provisioned successfully.')

    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command() -> None:
        applied = upgrade_database()
        click.echo(f"Database migrated ({len(applied)} applied).")

    @app.cli.command("upgrade-db")
    @with_appcontext
    def upgrade_db_command() -> None:
        applied = upgrade_database()
        click.echo(f"Database migrated ({len(applied)} applied).")

    @app.cli.command("sync-runtime-schema")
    @with_appcontext
    def sync_runtime_schema_command() -> None:
        applied = upgrade_database()
        click.echo(f"Runtime schema migration compatibility completed ({len(applied)} applied).")

    @app.cli.command("seed-data")
    @click.option("--demo/--no-demo", default=None)
    @with_appcontext
    def seed_data_command(demo: bool | None) -> None:
        from .seed.bootstrap import seed_all

        enable_demo_data = current_app.config["ENABLE_DEMO_DATA"] if demo is None else demo
        seed_all(enable_demo_data=enable_demo_data)
        click.echo(f"Seed completed (demo={'on' if enable_demo_data else 'off'}).")

    @app.cli.command("bootstrap-app")
    @click.option("--demo/--no-demo", default=None)
    @with_appcontext
    def bootstrap_app_command(demo: bool | None) -> None:
        from .seed.bootstrap import seed_all

        _ensure_models_loaded()
        enable_demo_data = current_app.config["ENABLE_DEMO_DATA"] if demo is None else demo
        upgrade_database()
        seed_all(enable_demo_data=enable_demo_data)
        click.echo(f"Bootstrap completed (demo={'on' if enable_demo_data else 'off'}).")

    @app.cli.command("export-audit-logs")
    @with_appcontext
    def export_audit_logs_command() -> None:
        from .services.audit_log_archive import run_daily_admin_log_exports

        result = run_daily_admin_log_exports()
        click.echo(str(result))

    @app.cli.command("send-weekly-parent-progress-emails")
    @click.option("--force", is_flag=True, help="Ignore weekly dedupe keys and send again.")
    @with_appcontext
    def send_weekly_parent_progress_emails_command(force: bool) -> None:
        from .core.db import db
        from .services.notifications import run_weekly_parent_progress_reminders

        result = run_weekly_parent_progress_reminders(force=force)
        db.session.commit()
        click.echo(str(result))

    @app.cli.command("backfill-assignment-images")
    @with_appcontext
    def backfill_assignment_images_command() -> None:
        from .core.db import db
        from .services.assignment_images import backfill_assignment_placeholders

        attached = backfill_assignment_placeholders()
        db.session.commit()
        click.echo(f"Assignment placeholders attached: {attached}.")
