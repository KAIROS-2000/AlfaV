from __future__ import annotations

from sqlalchemy import inspect

from app.models.notifications import (
    EmailNotificationLog,
    UserNotification,
    UserNotificationPreference,
)

revision = "0021_user_notifications"
description = "User notifications, email preferences, and email delivery log"


def _create_table_with_indexes(table, db) -> None:
    table.create(bind=db.engine, checkfirst=True)
    for index in table.indexes:
        index.create(bind=db.engine, checkfirst=True)


def upgrade(db) -> None:
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "user_notifications" not in tables:
        _create_table_with_indexes(UserNotification.__table__, db)

    if "user_notification_preferences" not in tables:
        _create_table_with_indexes(UserNotificationPreference.__table__, db)

    if "email_notification_logs" not in tables:
        _create_table_with_indexes(EmailNotificationLog.__table__, db)
