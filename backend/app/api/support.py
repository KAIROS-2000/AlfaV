from __future__ import annotations

from flask import Blueprint, request

from ..core.db import db
from ..core.pagination import pagination_params
from ..core.security import auth_required
from ..models.user import User, UserRole
from ..services import notifications
from ..services import support_tickets as svc
from ..services import bug_hunter as bug_svc
from ..services.assignment_images import ImageValidationError, MAX_UPLOAD_BYTES, reencode_uploaded_image

support_bp = Blueprint("support", __name__)

_TICKET_CREATORS = [UserRole.STUDENT, UserRole.TEACHER, UserRole.PARENT, UserRole.MANAGER]
_BUG_HUNTER_REPORTERS = [
    UserRole.STUDENT,
    UserRole.TEACHER,
    UserRole.PARENT,
    UserRole.ADMIN,
    UserRole.SUPERADMIN,
]
_STAFF = [UserRole.ADMIN, UserRole.SUPERADMIN]


def _parse_positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _safe_limit(value, *, default: int = 50, maximum: int = 100) -> int:
    parsed = _parse_positive_int(value)
    if parsed is None:
        return default
    return min(parsed, maximum)


@support_bp.post("/tickets")
@auth_required(_TICKET_CREATORS)
def create_ticket(user: User):
    data = request.get_json(silent=True) or {}
    result = svc.create_ticket(
        user,
        category=str(data.get("category") or ""),
        subject=str(data.get("subject") or ""),
        description=str(data.get("description") or ""),
    )
    if isinstance(result, tuple):
        payload, status = result
        return payload, status
    ticket = result
    notifications.notify_support_ticket_created(user, ticket)
    db.session.commit()
    return {
        "ticket": svc.ticket_peer_summary(ticket, viewer_id=user.id),
        "detail": svc.ticket_detail_payload(user, ticket),
    }, 201


@support_bp.get("/tickets")
@auth_required(_TICKET_CREATORS)
def list_my_tickets(user: User):
    page, page_size = pagination_params(request.args)
    return svc.user_inbox_summary(user, page=page, page_size=page_size)


@support_bp.get("/tickets/<int:ticket_id>")
@auth_required()
def get_ticket(user: User, ticket_id: int):
    ticket, err = svc.get_ticket_for(user, ticket_id)
    if err == "not_found":
        return {"message": "Обращение не найдено."}, 404
    if err == "forbidden":
        return {"message": "Forbidden"}, 403
    assert ticket is not None
    detail = svc.ticket_detail_payload(user, ticket)
    limit = _safe_limit(request.args.get("limit"), default=80, maximum=svc.LIST_MESSAGES_LIMIT)
    before_id = _parse_positive_int(request.args.get("before_id"))
    messages = svc.list_ticket_messages(user, ticket, limit=limit, before_id=before_id)
    return {
        **detail,
        "messages": [svc.message_payload(m, user) for m in messages],
        "limit": limit,
        "before_id": before_id,
    }


@support_bp.post("/tickets/<int:ticket_id>/messages")
@auth_required()
def post_ticket_message(user: User, ticket_id: int):
    ticket, err = svc.get_ticket_for(user, ticket_id)
    if err == "not_found":
        return {"message": "Обращение не найдено."}, 404
    if err == "forbidden":
        return {"message": "Forbidden"}, 403
    assert ticket is not None

    data = request.get_json(silent=True) or {}
    message, error = svc.append_message(user, ticket, str(data.get("body") or ""))
    if error:
        payload, status = error
        return payload, status
    assert message is not None
    notifications.notify_support_ticket_message(user, ticket, message)
    db.session.commit()
    return {
        "message": svc.message_payload(message, user),
        "ticket": svc.ticket_peer_summary(ticket, viewer_id=user.id),
    }, 201


@support_bp.post("/tickets/<int:ticket_id>/read")
@auth_required()
def post_ticket_read(user: User, ticket_id: int):
    ticket, err = svc.get_ticket_for(user, ticket_id)
    if err == "not_found":
        return {"message": "Обращение не найдено."}, 404
    if err == "forbidden":
        return {"message": "Forbidden"}, 403
    assert ticket is not None

    data = request.get_json(silent=True) or {}
    raw = data.get("last_message_id")
    last_id = _parse_positive_int(raw) if raw is not None else None

    result = svc.mark_read(user, ticket, last_id)
    if "error" in result:
        payload, status = result["error"]
        return payload, status
    db.session.commit()
    out = {k: v for k, v in result.items() if k != "error"}
    return out


@support_bp.get("/staff/tickets")
@auth_required(_STAFF)
def staff_list(user: User):
    status_filter = str(request.args.get("status") or "all")
    page, page_size = pagination_params(request.args)
    rows, pagination = svc.staff_ticket_rows(
        user,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    total_unread = svc.staff_inbox_summary(user)["total_unread"]
    return {"total_unread": total_unread, "tickets": rows, "pagination": pagination}


@support_bp.get("/staff/tickets/<int:ticket_id>")
@auth_required(_STAFF)
def staff_get_ticket(user: User, ticket_id: int):
    ticket, err = svc.get_ticket_for(user, ticket_id)
    if err == "not_found":
        return {"message": "Обращение не найдено."}, 404
    assert ticket is not None
    detail = svc.ticket_detail_payload(user, ticket)
    limit = _safe_limit(request.args.get("limit"), default=80, maximum=svc.LIST_MESSAGES_LIMIT)
    before_id = _parse_positive_int(request.args.get("before_id"))
    messages = svc.list_ticket_messages(user, ticket, limit=limit, before_id=before_id)
    return {
        **detail,
        "messages": [svc.message_payload(m, user) for m in messages],
        "limit": limit,
        "before_id": before_id,
    }


@support_bp.patch("/staff/tickets/<int:ticket_id>")
@auth_required(_STAFF)
def staff_patch_ticket(user: User, ticket_id: int):
    ticket, err = svc.get_ticket_for(user, ticket_id)
    if err == "not_found":
        return {"message": "Обращение не найдено."}, 404
    assert ticket is not None

    data = request.get_json(silent=True) or {}
    _, error = svc.staff_set_status(user, ticket, str(data.get("status") or ""))
    if error:
        payload, status = error
        return payload, status
    db.session.commit()
    return {
        "ticket": {
            "id": ticket.id,
            "status": ticket.status,
            "updated_at": svc.iso_timestamp(ticket.updated_at),
        }
    }


@support_bp.post("/staff/tickets/<int:ticket_id>/messages")
@auth_required(_STAFF)
def staff_post_message(user: User, ticket_id: int):
    ticket, err = svc.get_ticket_for(user, ticket_id)
    if err == "not_found":
        return {"message": "Обращение не найдено."}, 404
    assert ticket is not None

    data = request.get_json(silent=True) or {}
    message, error = svc.append_message(user, ticket, str(data.get("body") or ""))
    if error:
        payload, status = error
        return payload, status
    assert message is not None
    notifications.notify_support_ticket_message(user, ticket, message)
    db.session.commit()
    return {
        "message": svc.message_payload(message, user),
        "ticket_summary": {
            "ticket_id": ticket.id,
            "status": ticket.status,
            "subject": ticket.subject,
            "updated_at": svc.iso_timestamp(ticket.updated_at),
        },
    }, 201


@support_bp.post("/bug-reports")
@auth_required(_BUG_HUNTER_REPORTERS)
def create_bug_report(user: User):
    description = request.form.get("description") or ""
    reproduction_steps = request.form.get("reproduction_steps") or ""
    user_journey_path = request.form.get("user_journey_path") or ""
    screenshot_asset_id = None

    upload = request.files.get("screenshot")
    if upload is not None and upload.filename:
        raw_bytes = upload.read()
        if len(raw_bytes) > MAX_UPLOAD_BYTES:
            return {'message': f'Скриншот больше {MAX_UPLOAD_BYTES // (1024 * 1024)} МБ.'}, 413
        try:
            asset = reencode_uploaded_image(raw_bytes, uploaded_by_id=user.id)
        except ImageValidationError as exc:
            return {'message': str(exc)}, 400
        screenshot_asset_id = asset.id

    payload, status = bug_svc.create_report(
        user,
        description=description,
        reproduction_steps=reproduction_steps,
        user_journey_path=user_journey_path,
        screenshot_asset_id=screenshot_asset_id,
    )
    if status >= 400:
        db.session.rollback()
        return payload, status
    db.session.commit()
    return payload, status


@support_bp.get("/bug-reports/me")
@auth_required(_BUG_HUNTER_REPORTERS)
def list_my_bug_reports(user: User):
    page, page_size = pagination_params(request.args)
    return bug_svc.list_my_reports(user, page=page, page_size=page_size)


@support_bp.get("/staff/bug-reports")
@auth_required(_STAFF)
def staff_list_bug_reports(_user: User):
    st_raw = request.args.get("status")
    status_filter = None if not st_raw or str(st_raw).strip() == '' else str(st_raw).strip()
    page, page_size = pagination_params(request.args)
    rows, pagination = bug_svc.staff_list_rows(
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return {
        "reports": [r.to_dict(include_private=True) for r in rows],
        "xp_reward_on_approval": bug_svc.get_bug_hunter_approved_xp(),
        "pagination": pagination,
    }


@support_bp.get("/staff/bug-hunter/settings")
@auth_required(_STAFF)
def staff_get_bug_hunter_settings(_user: User):
    return {
        "approved_xp": bug_svc.get_bug_hunter_approved_xp(),
        "max_xp": bug_svc.BUG_HUNTER_XP_MAX,
    }


@support_bp.patch("/staff/bug-hunter/settings")
@auth_required(_STAFF)
def staff_patch_bug_hunter_settings(_user: User):
    data = request.get_json(silent=True) or {}
    payload, status = bug_svc.set_bug_hunter_approved_xp(data.get("approved_xp"))
    if status >= 400:
        db.session.rollback()
        return payload, status
    db.session.commit()
    return payload, status


@support_bp.patch("/staff/bug-reports/<int:report_id>")
@auth_required(_STAFF)
def staff_moderate_bug_report(user: User, report_id: int):
    data = request.get_json(silent=True) or {}
    new_status = str(data.get("moderation_status") or "").strip().lower()
    raw_note = data.get("moderator_note")
    note_val = None if raw_note is None else str(raw_note)

    payload, status = bug_svc.staff_moderate(
        user, report_id, new_status=new_status, note=note_val
    )
    if status >= 400:
        db.session.rollback()
        return payload, status
    db.session.commit()
    return payload, status
