"""Bug hunter reports: user-submitted issues with optional screenshot; XP on staff approval."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import current_app

from ..core.db import db
from ..models.bug_hunter import (
    BUG_REPORT_STATUS_APPROVED,
    BUG_REPORT_STATUS_PENDING,
    BUG_REPORT_STATUS_REJECTED,
    BugHunterReport,
)
from ..models.platform_kv import PlatformKv
from ..models.user import User


MAX_DESCRIPTION_LEN = 12_000
MAX_REPRO_STEPS_LEN = 24_000
MAX_JOURNEY_LEN = 24_000
MAX_MODERATOR_NOTE_LEN = 4000

BUG_HUNTER_APPROVED_XP_KEY = "bug_hunter_approved_xp"
BUG_HUNTER_XP_MAX = 10_000


def _fallback_xp_from_config() -> int:
    return max(0, int(current_app.config.get("BUG_HUNTER_APPROVED_XP") or 0))


def get_bug_hunter_approved_xp() -> int:
    row = db.session.get(PlatformKv, BUG_HUNTER_APPROVED_XP_KEY)
    if row is not None and (row.value or "").strip() != "":
        try:
            return max(0, min(BUG_HUNTER_XP_MAX, int(str(row.value).strip())))
        except (TypeError, ValueError):
            pass
    return _fallback_xp_from_config()


def set_bug_hunter_approved_xp(raw) -> tuple[dict, int]:
    """Persist XP for accepted bug reports (0 … BUG_HUNTER_XP_MAX)."""
    try:
        xp = int(raw)
    except (TypeError, ValueError):
        return {"message": "Некорректное значение XP (нужно целое число)."}, 400
    if xp < 0 or xp > BUG_HUNTER_XP_MAX:
        return {"message": f"XP должно быть от 0 до {BUG_HUNTER_XP_MAX}."}, 400

    row = db.session.get(PlatformKv, BUG_HUNTER_APPROVED_XP_KEY)
    if row is None:
        db.session.add(PlatformKv(key=BUG_HUNTER_APPROVED_XP_KEY, value=str(xp)))
    else:
        row.value = str(xp)
    db.session.flush()
    return {"approved_xp": xp, "max_xp": BUG_HUNTER_XP_MAX}, 200


def _clip_text(value: str, limit: int) -> str:
    s = (value or "").strip()
    if len(s) > limit:
        return s[:limit]
    return s


def create_report(
    user: User,
    *,
    description: str,
    reproduction_steps: str,
    user_journey_path: str,
    screenshot_asset_id: int | None,
) -> tuple[dict, int]:
    desc = _clip_text(description, MAX_DESCRIPTION_LEN)
    steps = _clip_text(reproduction_steps, MAX_REPRO_STEPS_LEN)
    journey = _clip_text(user_journey_path, MAX_JOURNEY_LEN)
    if len(desc) < 8:
        return {'message': 'Опишите проблему подробнее (минимум 8 символов).'}, 400
    if len(steps) < 8:
        return {'message': 'Укажите шаги воспроизведения (минимум 8 символов).'}, 400
    if len(journey) < 4:
        return {'message': 'Укажите маршрут по платформе (минимум 4 символа).'}, 400

    row = BugHunterReport(
        user_id=user.id,
        description=desc,
        reproduction_steps=steps,
        user_journey_path=journey,
        screenshot_asset_id=screenshot_asset_id,
        moderation_status=BUG_REPORT_STATUS_PENDING,
    )
    db.session.add(row)
    db.session.flush()
    approved_xp_hint = get_bug_hunter_approved_xp()
    return {
        'report': row.to_dict(),
        'xp_on_approval_preview': approved_xp_hint,
        'message': 'Спасибо! После проверки модератор может начислить XP.',
    }, 201


def list_my_reports(user: User, *, limit: int = 50) -> dict:
    q = (
        BugHunterReport.query.filter_by(user_id=user.id)
        .order_by(BugHunterReport.created_at.desc(), BugHunterReport.id.desc())
        .limit(min(max(limit, 1), 100))
        .all()
    )
    return {
        'reports': [r.to_dict() for r in q],
        'xp_reward_on_approval': get_bug_hunter_approved_xp(),
    }


def staff_list_rows(*, status: str | None = None, limit: int = 100) -> list[BugHunterReport]:
    q = BugHunterReport.query.order_by(
        BugHunterReport.created_at.desc(), BugHunterReport.id.desc()
    )
    if status and status != 'all':
        q = q.filter(BugHunterReport.moderation_status == status)
    return q.limit(min(max(limit, 1), 200)).all()


def staff_moderate(
    moderator: User, report_id: int, *, new_status: str, note: str | None = None
) -> tuple[dict, int]:
    row = db.session.get(BugHunterReport, report_id)
    if row is None:
        return {'message': 'Репорт не найден.'}, 404

    if row.moderation_status != BUG_REPORT_STATUS_PENDING:
        return {'message': 'Решение уже принято для этого репорта.'}, 409

    note_clean = _clip_text(note or '', MAX_MODERATOR_NOTE_LEN) or None

    if new_status == BUG_REPORT_STATUS_APPROVED:
        # H5: a moderator cannot approve their own report and grant themselves XP.
        if row.user_id == moderator.id:
            return {'message': 'Нельзя одобрить собственный репорт.'}, 403
        xp_amount = get_bug_hunter_approved_xp()
        reporter = db.session.get(User, row.user_id)
        if reporter is None:
            return {'message': 'Пользователь не найден.'}, 400
        if xp_amount > 0:
            reporter.add_xp(xp_amount)
        row.xp_awarded = xp_amount
        row.moderation_status = BUG_REPORT_STATUS_APPROVED
        row.moderated_by_id = moderator.id
        row.moderated_at = datetime.now(UTC)
        row.moderator_note = note_clean
        return {
            'report': row.to_dict(include_private=True),
            'user': reporter.to_dict(),
        }, 200

    if new_status == BUG_REPORT_STATUS_REJECTED:
        row.moderation_status = BUG_REPORT_STATUS_REJECTED
        row.moderated_by_id = moderator.id
        row.moderated_at = datetime.now(UTC)
        row.moderator_note = note_clean
        row.xp_awarded = 0
        return {'report': row.to_dict(include_private=True)}, 200

    return {'message': 'Некорректный статус (ожидалось approved или rejected).'}, 400
