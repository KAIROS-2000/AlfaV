from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from ..core.db import db

JSONType = JSONB().with_variant(db.JSON(), "sqlite")


class UserNotification(db.Model):
    __tablename__ = "user_notifications"
    __table_args__ = (
        Index("ix_user_notification_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_user_notification_recipient_read", "recipient_user_id", "read_at"),
        Index("ix_user_notification_type", "type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    type = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    href = db.Column(db.String(500), nullable=True)
    data_json = db.Column(JSONType, nullable=False, default=dict)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    recipient = db.relationship("User", foreign_keys=[recipient_user_id])
    actor = db.relationship("User", foreign_keys=[actor_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipient_user_id": self.recipient_user_id,
            "actor_user_id": self.actor_user_id,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "href": self.href,
            "data": self.data_json if isinstance(self.data_json, dict) else {},
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserNotificationPreference(db.Model):
    __tablename__ = "user_notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_notification_preferences_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_messages_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_assignments_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_parent_achievements_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_parent_weekly_progress_enabled = db.Column(db.Boolean, nullable=False, default=True)
    email_staff_notifications_enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = db.relationship("User", foreign_keys=[user_id])

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email_notifications_enabled": bool(self.email_notifications_enabled),
            "email_messages_enabled": bool(self.email_messages_enabled),
            "email_assignments_enabled": bool(self.email_assignments_enabled),
            "email_parent_achievements_enabled": bool(self.email_parent_achievements_enabled),
            "email_parent_weekly_progress_enabled": bool(self.email_parent_weekly_progress_enabled),
            "email_staff_notifications_enabled": bool(self.email_staff_notifications_enabled),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EmailNotificationLog(db.Model):
    __tablename__ = "email_notification_logs"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_email_notification_logs_dedupe_key"),
        Index("ix_email_notification_log_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_email_notification_log_event", "event_type"),
        Index("ix_email_notification_log_status", "status"),
        Index("ix_email_notification_log_related", "related_type", "related_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey("user_notifications.id", ondelete="SET NULL"), nullable=True)
    recipient_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    recipient_email = db.Column(db.String(120), nullable=False)
    event_type = db.Column(db.String(80), nullable=False)
    related_type = db.Column(db.String(80), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)
    dedupe_key = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(24), nullable=False)
    provider = db.Column(db.String(60), nullable=True)
    message_id = db.Column(db.String(120), nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    notification = db.relationship("UserNotification", foreign_keys=[notification_id])
    recipient = db.relationship("User", foreign_keys=[recipient_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "notification_id": self.notification_id,
            "recipient_user_id": self.recipient_user_id,
            "recipient_email": self.recipient_email,
            "event_type": self.event_type,
            "related_type": self.related_type,
            "related_id": self.related_id,
            "dedupe_key": self.dedupe_key,
            "status": self.status,
            "provider": self.provider,
            "message_id": self.message_id,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
