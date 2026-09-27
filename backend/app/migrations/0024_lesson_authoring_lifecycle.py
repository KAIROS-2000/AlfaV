from __future__ import annotations

from contextlib import nullcontext

from sqlalchemy import inspect, text


revision = "0024_lesson_authoring_lifecycle"
description = "Add draft lifecycle, ownership, metadata, and optimistic version fields to lessons"


def upgrade(db, *, connection=None) -> None:  # noqa: ANN001
    bind = connection or db.engine
    inspector = inspect(bind)
    if "lessons" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("lessons")}
    dialect = bind.dialect.name
    json_type = "JSONB" if dialect == "postgresql" else "JSON"
    statements = {
        "created_by_id": "ALTER TABLE lessons ADD COLUMN created_by_id INTEGER NULL",
        "updated_at": "ALTER TABLE lessons ADD COLUMN updated_at TIMESTAMP NULL",
        "version": "ALTER TABLE lessons ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
        "published_at": "ALTER TABLE lessons ADD COLUMN published_at TIMESTAMP NULL",
        "archived_at": "ALTER TABLE lessons ADD COLUMN archived_at TIMESTAMP NULL",
        "authoring_metadata": (
            f"ALTER TABLE lessons ADD COLUMN authoring_metadata {json_type} "
            f"NOT NULL DEFAULT '{{}}'"
        ),
    }
    connection_scope = nullcontext(connection) if connection is not None else db.engine.begin()
    with connection_scope as conn:
        for column, statement in statements.items():
            if column not in columns:
                conn.execute(text(statement))
        conn.execute(
            text("UPDATE lessons SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
        )
