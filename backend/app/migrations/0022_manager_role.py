from __future__ import annotations

from sqlalchemy import text


revision = '0022_manager_role'
description = 'Add the manager role to user accounts'


def upgrade(db) -> None:
    """Add the enum value without touching existing user rows.

    SQLite persists SQLAlchemy enums as text, while deployed PostgreSQL databases
    require the new label to be registered explicitly.
    """
    if db.engine.dialect.name != 'postgresql':
        return
    with db.engine.begin() as connection:
        try:
            connection.execute(text("ALTER TYPE userrole ADD VALUE 'manager'"))
        except Exception:
            # The label may already have been added during a partially applied
            # deploy, or the installation may use a VARCHAR role column.
            pass
