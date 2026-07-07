from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, request

from ..core.db import db
from ..core.security import auth_required
from ..models.notifications import UserNotification
from ..models.user import User
from ..services.notifications import get_or_create_preferences

notifications_bp = Blueprint("notifications", __name__)

PREFERENCE_FIELDS = {
    "email_notifications_enabled",
    "email_messages_enabled",
    "email_assignments_enabled",
    "email_parent_achievements_enabled",
    "email_parent_weekly_progress_enabled",
    "email_staff_notifications_enabled",
}


def _parse_positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


@notifications_bp.get("")
@auth_required()
def list_notifications(user: User):
    limit = min(_parse_positive_int(request.args.get("limit")) or 50, 100)
    unread_only = str(request.args.get("unread") or "").strip().lower() in {"1", "true", "yes"}
    query = UserNotification.query.filter_by(recipient_user_id=user.id)
    if unread_only:
        query = query.filter(UserNotification.read_at.is_(None))
    rows = query.order_by(UserNotification.created_at.desc(), UserNotification.id.desc()).limit(limit).all()
    total_unread = UserNotification.query.filter_by(
        recipient_user_id=user.id,
        read_at=None,
    ).count()
    return {
        "notifications": [row.to_dict() for row in rows],
        "total_unread": total_unread,
        "limit": limit,
    }


@notifications_bp.patch("/<int:notification_id>/read")
@auth_required()
def mark_notification_read(user: User, notification_id: int):
    row = UserNotification.query.filter_by(id=notification_id, recipient_user_id=user.id).first()
    if row is None:
        return {"message": "Уведомление не найдено."}, 404
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        db.session.commit()
    return {"notification": row.to_dict()}


@notifications_bp.patch("/read-all")
@auth_required()
def mark_all_notifications_read(user: User):
    now = datetime.now(UTC)
    updated = (
        UserNotification.query.filter_by(recipient_user_id=user.id, read_at=None)
        .update({"read_at": now}, synchronize_session=False)
    )
    db.session.commit()
    return {"updated": updated}


@notifications_bp.get("/preferences")
@auth_required()
def get_preferences(user: User):
    pref = get_or_create_preferences(user)
    db.session.commit()
    return {"preferences": pref.to_dict()}


@notifications_bp.patch("/preferences")
@auth_required()
def patch_preferences(user: User):
    data = request.get_json(silent=True) or {}
    pref = get_or_create_preferences(user)
    changed: list[str] = []
    for field in PREFERENCE_FIELDS:
        if field not in data:
            continue
        setattr(pref, field, bool(data[field]))
        changed.append(field)
    pref.updated_at = datetime.now(UTC)
    db.session.commit()
    return {"preferences": pref.to_dict(), "changed": changed}
