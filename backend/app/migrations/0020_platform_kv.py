from __future__ import annotations

from sqlalchemy import inspect

from app.models.platform_kv import PlatformKv

revision = "0020_platform_kv"
description = "Platform key/value settings (e.g. bug hunter approved XP)"


def upgrade(db) -> None:
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "platform_kv" not in tables:
        PlatformKv.__table__.create(bind=db.engine, checkfirst=True)
