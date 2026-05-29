"""Small key/value rows for operator-tunable defaults (Bug Hunter XP, etc.)."""

from __future__ import annotations

from datetime import UTC, datetime

from ..core.db import db


class PlatformKv(db.Model):
    __tablename__ = "platform_kv"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
