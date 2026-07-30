from __future__ import annotations

from sqlalchemy import text


revision = '0023_manager_role_enum_compatibility'
description = 'Ensure PostgreSQL userrole enum supports SQLAlchemy manager member'


def upgrade(db) -> None:
    """Repair deployments where the previous migration added ``manager``.

    SQLAlchemy stores :class:`UserRole` member names by default, so inserts
    bind ``MANAGER`` while the API exposes the lowercase ``manager`` value.
    The original manager migration used the API value and may already be
    recorded as applied. This additive compatibility migration therefore adds
    the required uppercase label independently and remains safe to rerun.
    """
    if db.engine.dialect.name != 'postgresql':
        return

    with db.engine.begin() as connection:
        enum_exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_type
                    WHERE typname = 'userrole' AND typtype = 'e'
                )
                """
            )
        ).scalar()
        if enum_exists:
            connection.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'MANAGER'"))
