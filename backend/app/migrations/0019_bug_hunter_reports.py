from __future__ import annotations

from sqlalchemy import inspect

from app.models.bug_hunter import BugHunterReport

revision = "0019_bug_hunter_reports"
description = "Bug hunter reports with optional screenshot asset and moderated XP"


def upgrade(db) -> None:
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "bug_hunter_reports" not in tables:
        BugHunterReport.__table__.create(bind=db.engine, checkfirst=True)
        for index in BugHunterReport.__table__.indexes:
            index.create(bind=db.engine, checkfirst=True)
