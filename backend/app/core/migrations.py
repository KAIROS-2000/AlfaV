from __future__ import annotations

import importlib
import inspect as python_inspect
import pkgutil
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import Connection, Engine, inspect, text

from .db import db


@dataclass(frozen=True)
class Migration:
    revision: str
    description: str
    module_name: str


# A stable, application-specific signed bigint used with PostgreSQL's
# session-level advisory lock. Session locks survive the per-migration commits
# below and are automatically released if the deploy process disconnects.
POSTGRES_MIGRATION_ADVISORY_LOCK_ID = 764_891_273_012_345_678


def _ensure_models_loaded() -> None:
    from .. import models  # noqa: F401


def _migration_modules() -> list[Migration]:
    from .. import migrations

    rows: list[Migration] = []
    for module_info in pkgutil.iter_modules(migrations.__path__):
        if not module_info.name.startswith(('m', 'v')) and not module_info.name[0].isdigit():
            continue
        module = importlib.import_module(f'{migrations.__name__}.{module_info.name}')
        revision = getattr(module, 'revision', module_info.name)
        description = getattr(module, 'description', '')
        rows.append(Migration(revision=revision, description=description, module_name=module.__name__))
    return sorted(rows, key=lambda item: item.revision)


def _ensure_migration_table(connection: Connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                revision VARCHAR(120) PRIMARY KEY,
                description VARCHAR(255) NOT NULL DEFAULT '',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _applied_revisions(connection: Connection) -> set[str]:
    inspector = inspect(connection)
    if 'schema_migrations' not in inspector.get_table_names():
        return set()
    rows = connection.execute(text('SELECT revision FROM schema_migrations')).all()
    return {str(row[0]) for row in rows}


def _record_migration(connection: Connection, migration: Migration) -> None:
    connection.execute(
        text(
            """
            INSERT INTO schema_migrations (revision, description)
            VALUES (:revision, :description)
            """
        ),
        {'revision': migration.revision, 'description': migration.description[:255]},
    )


@contextmanager
def _locked_migration_connection(engine: Engine) -> Iterator[Connection]:
    """Yield one connection while serializing PostgreSQL deployers.

    The advisory lock is session-scoped rather than transaction-scoped so it
    stays held while individual migration transactions commit. SQLite keeps
    its existing behavior and executes no PostgreSQL-specific SQL.
    """

    connection = engine.connect()
    is_postgresql = engine.dialect.name == 'postgresql'
    try:
        if is_postgresql:
            connection.execute(
                text('SELECT pg_advisory_lock(:lock_id)'),
                {'lock_id': POSTGRES_MIGRATION_ADVISORY_LOCK_ID},
            )
            # End SQLAlchemy's implicit transaction without releasing the
            # session-level lock.
            connection.commit()
        yield connection
    finally:
        if connection.in_transaction():
            connection.rollback()
        if is_postgresql:
            connection.execute(
                text('SELECT pg_advisory_unlock(:lock_id)'),
                {'lock_id': POSTGRES_MIGRATION_ADVISORY_LOCK_ID},
            )
            connection.commit()
        connection.close()


def _supports_atomic_connection(module) -> bool:  # noqa: ANN001
    try:
        parameters = python_inspect.signature(module.upgrade).parameters
    except (TypeError, ValueError):
        return False
    return 'connection' in parameters


def _apply_migration(connection: Connection, migration: Migration) -> None:
    module = importlib.import_module(migration.module_name)
    if _supports_atomic_connection(module):
        # Preferred API: DDL/data updates and revision recording use the same
        # transaction. New migrations should accept ``connection=``.
        with connection.begin():
            module.upgrade(db, connection=connection)
            _record_migration(connection, migration)
        return

    # Legacy migrations manage their own engine transactions or call
    # Flask-SQLAlchemy create_all(). The advisory lock still prevents another
    # PostgreSQL deployer from entering this gap. They are idempotent, so a
    # crash before recording is recoverable on retry.
    module.upgrade(db)
    with connection.begin():
        _record_migration(connection, migration)


def upgrade_database() -> list[str]:
    """Apply all pending schema migrations under one deployer lock.

    Returns the revisions applied in this call so CLI/CI smoke checks can assert
    deterministic migration execution without parsing logs.
    """

    _ensure_models_loaded()
    applied_now: list[str] = []

    with _locked_migration_connection(db.engine) as connection:
        with connection.begin():
            _ensure_migration_table(connection)
        with connection.begin():
            applied = _applied_revisions(connection)

        for migration in _migration_modules():
            if migration.revision in applied:
                continue
            _apply_migration(connection, migration)
            applied.add(migration.revision)
            applied_now.append(migration.revision)

    return applied_now
