from __future__ import annotations

from contextlib import nullcontext

from sqlalchemy import inspect, text


revision = "0025_lesson_authoring_schema_constraints"
description = "Align lesson authoring timestamps, ownership foreign key, and index with the ORM"


def _quote_identifier(db, identifier: str) -> str:
    return db.engine.dialect.identifier_preparer.quote(identifier)


def upgrade(db, *, connection=None) -> None:  # noqa: ANN001
    bind = connection or db.engine
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "lessons" not in table_names:
        return

    columns = {column["name"]: column for column in inspector.get_columns("lessons")}
    dialect = bind.dialect.name
    statements: list[str] = []

    if "updated_at" in columns:
        statements.append("UPDATE lessons SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")

    if dialect == "postgresql":
        # Migration 0024 used an unqualified TIMESTAMP. Existing values were
        # produced as UTC, so explicitly interpret those naive values as UTC
        # while converting the three ORM timezone-aware columns.
        for column_name in ("updated_at", "published_at", "archived_at"):
            column = columns.get(column_name)
            if column is not None and getattr(column.get("type"), "timezone", None) is not True:
                quoted_column = _quote_identifier(db, column_name)
                statements.append(
                    f"ALTER TABLE lessons ALTER COLUMN {quoted_column} TYPE TIMESTAMP WITH TIME ZONE "
                    f"USING {quoted_column} AT TIME ZONE 'UTC'"
                )
        if "updated_at" in columns and columns["updated_at"].get("nullable", True):
            statements.append("ALTER TABLE lessons ALTER COLUMN updated_at SET NOT NULL")

        if "created_by_id" in columns and "users" in table_names:
            statements.append(
                "UPDATE lessons SET created_by_id = NULL "
                "WHERE created_by_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM users WHERE users.id = lessons.created_by_id)"
            )
            owner_foreign_keys = [
                foreign_key
                for foreign_key in inspector.get_foreign_keys("lessons")
                if foreign_key.get("constrained_columns") == ["created_by_id"]
            ]
            correct_foreign_key = any(
                foreign_key.get("referred_table") == "users"
                and foreign_key.get("referred_columns") == ["id"]
                and str((foreign_key.get("options") or {}).get("ondelete") or "").upper() == "SET NULL"
                for foreign_key in owner_foreign_keys
            )
            if not correct_foreign_key:
                for foreign_key in owner_foreign_keys:
                    constraint_name = foreign_key.get("name")
                    if constraint_name:
                        statements.append(
                            "ALTER TABLE lessons DROP CONSTRAINT "
                            f"{_quote_identifier(db, constraint_name)}"
                        )
                statements.append(
                    "ALTER TABLE lessons ADD CONSTRAINT fk_lessons_created_by_id_users "
                    "FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL"
                )

    if "created_by_id" in columns:
        indexes = inspector.get_indexes("lessons")
        if not any(index.get("column_names") == ["created_by_id"] for index in indexes):
            statements.append("CREATE INDEX ix_lessons_created_by_id ON lessons (created_by_id)")

    connection_scope = nullcontext(connection) if connection is not None else db.engine.begin()
    with connection_scope as connection:
        for statement in statements:
            connection.execute(text(statement))
