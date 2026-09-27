from __future__ import annotations

from contextlib import nullcontext

from sqlalchemy import inspect, text


revision = "0026_user_legal_acceptance"
description = "Persist the legal document version and timestamp accepted during registration"


def upgrade(db, *, connection=None) -> None:  # noqa: ANN001
    bind = connection or db.engine
    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    timestamp_type = "TIMESTAMP WITH TIME ZONE" if bind.dialect.name == "postgresql" else "TIMESTAMP"
    statements = {
        "legal_documents_version": (
            "ALTER TABLE users ADD COLUMN legal_documents_version VARCHAR(64) NULL"
        ),
        "legal_documents_accepted_at": (
            f"ALTER TABLE users ADD COLUMN legal_documents_accepted_at {timestamp_type} NULL"
        ),
    }
    connection_scope = nullcontext(connection) if connection is not None else db.engine.begin()
    with connection_scope as connection:
        for column_name, statement in statements.items():
            if column_name not in columns:
                connection.execute(text(statement))
