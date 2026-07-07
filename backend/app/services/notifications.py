from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app

from ..core.db import db
from ..models.learning import (
    Assignment,
    AssignmentSubmission,
    ClassMembership,
    Classroom,
)
from ..models.notifications import (
    EmailNotificationLog,
    UserNotification,
    UserNotificationPreference,
)
from ..models.parent_cabinet import ParentChildLink, ParentConsentSettings
from ..models.support import SupportTicket, SupportTicketMessage
from ..models.user import User, UserRole

_log = logging.getLogger(__name__)

CATEGORY_MESSAGES = "messages"
CATEGORY_ASSIGNMENTS = "assignments"
CATEGORY_PARENT_ACHIEVEMENTS = "parent_achievements"
CATEGORY_PARENT_WEEKLY_PROGRESS = "parent_weekly_progress"
CATEGORY_STAFF = "staff"

SUCCESS_EMAIL_STATUSES = {"sent", "dry_run"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _absolute_url(href: str | None) -> str:
    target = (href or "").strip() or "/"
    lowered = target.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return target
    base = (current_app.config.get("FRONTEND_PUBLIC_URL") or current_app.config.get("CLIENT_URL") or "").strip()
    base = base.split(",")[0].strip().rstrip("/")
    if not base:
        return target
    if not target.startswith("/"):
        target = f"/{target}"
    return f"{base}{target}"


def _display_name(user: User | None, fallback: str = "Пользователь") -> str:
    if user is None:
        return fallback
    return (user.full_name or "").strip() or user.email or fallback


def _first_name(user: User | None, fallback: str = "Пользователь") -> str:
    name = _display_name(user, fallback)
    return name.split()[0] if name else fallback


def _preview(text: str | None, max_length: int = 140) -> str:
    body = " ".join(str(text or "").split())
    if len(body) <= max_length:
        return body
    return f"{body[: max_length - 1].rstrip()}…"


def _staff_href(user: User, admin_href: str) -> str:
    if user.role == UserRole.SUPERADMIN and admin_href.startswith("/admin"):
        return "/superadmin" + admin_href[len("/admin") :]
    return admin_href


def _preference_for(user: User) -> UserNotificationPreference | None:
    return UserNotificationPreference.query.filter_by(user_id=user.id).first()


def get_or_create_preferences(user: User) -> UserNotificationPreference:
    pref = _preference_for(user)
    if pref is not None:
        return pref
    pref = UserNotificationPreference(user_id=user.id)
    db.session.add(pref)
    db.session.flush()
    return pref


def _email_allowed_by_preferences(user: User, category: str | None) -> bool:
    pref = _preference_for(user)
    if pref is None:
        return True
    if not pref.email_notifications_enabled:
        return False
    if category == CATEGORY_MESSAGES:
        return bool(pref.email_messages_enabled)
    if category == CATEGORY_ASSIGNMENTS:
        return bool(pref.email_assignments_enabled)
    if category == CATEGORY_PARENT_ACHIEVEMENTS:
        return bool(pref.email_parent_achievements_enabled)
    if category == CATEGORY_PARENT_WEEKLY_PROGRESS:
        return bool(pref.email_parent_weekly_progress_enabled)
    if category == CATEGORY_STAFF:
        return bool(pref.email_staff_notifications_enabled)
    return True


def _existing_dedupe_log(dedupe_key: str | None) -> EmailNotificationLog | None:
    if not dedupe_key:
        return None
    return EmailNotificationLog.query.filter_by(dedupe_key=dedupe_key).first()


def _dedupe_already_succeeded(dedupe_key: str | None) -> bool:
    existing = _existing_dedupe_log(dedupe_key)
    return bool(existing and existing.status in SUCCESS_EMAIL_STATUSES)


def _recent_email_sent(
    *,
    recipient: User,
    event_type: str,
    related_type: str | None,
    related_id: int | None,
    minutes: int,
) -> bool:
    if minutes <= 0:
        return False
    cutoff = _utcnow() - timedelta(minutes=minutes)
    query = EmailNotificationLog.query.filter(
        EmailNotificationLog.recipient_user_id == recipient.id,
        EmailNotificationLog.event_type == event_type,
        EmailNotificationLog.created_at >= cutoff,
        EmailNotificationLog.status.in_(tuple(SUCCESS_EMAIL_STATUSES)),
    )
    if related_type:
        query = query.filter(EmailNotificationLog.related_type == related_type)
    if related_id is not None:
        query = query.filter(EmailNotificationLog.related_id == related_id)
    return db.session.query(query.exists()).scalar()


def _upsert_email_log(
    *,
    notification: UserNotification | None,
    recipient: User,
    event_type: str,
    related_type: str | None,
    related_id: int | None,
    dedupe_key: str | None,
    status: str,
    provider: str | None = None,
    message_id: str | None = None,
    error: str | None = None,
) -> EmailNotificationLog:
    log = _existing_dedupe_log(dedupe_key)
    if log is None:
        log = EmailNotificationLog(
            dedupe_key=dedupe_key,
            recipient_user_id=recipient.id,
            recipient_email=recipient.email,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
        )
        db.session.add(log)
    log.notification_id = notification.id if notification else None
    log.recipient_user_id = recipient.id
    log.recipient_email = recipient.email
    log.event_type = event_type
    log.related_type = related_type
    log.related_id = related_id
    log.status = status
    log.provider = provider
    log.message_id = message_id
    log.error = error
    log.created_at = log.created_at or _utcnow()
    log.sent_at = _utcnow() if status in SUCCESS_EMAIL_STATUSES else None
    db.session.flush()
    return log


def _skip_email_log(
    *,
    notification: UserNotification | None,
    recipient: User,
    event_type: str,
    related_type: str | None,
    related_id: int | None,
    dedupe_key: str | None,
    reason: str,
) -> EmailNotificationLog:
    return _upsert_email_log(
        notification=notification,
        recipient=recipient,
        event_type=event_type,
        related_type=related_type,
        related_id=related_id,
        dedupe_key=dedupe_key,
        status="skipped",
        provider="disabled",
        error=reason,
    )


def notify_user(
    recipient: User,
    *,
    event_type: str,
    title: str,
    body: str,
    href: str,
    actor: User | None = None,
    email_category: str | None = None,
    email: bool = True,
    action_label: str = "Открыть",
    details: list[tuple[str, str]] | None = None,
    metadata: dict[str, Any] | None = None,
    related_type: str | None = None,
    related_id: int | None = None,
    dedupe_key: str | None = None,
    cooldown_minutes: int = 0,
    create_inapp: bool = True,
    suppress_self_email: bool = True,
    allow_inactive_email: bool = False,
) -> dict[str, Any]:
    if email and _dedupe_already_succeeded(dedupe_key):
        return {"notification": None, "email_log": _existing_dedupe_log(dedupe_key), "email_status": "deduped"}

    notification = None
    if create_inapp:
        notification = UserNotification(
            recipient_user_id=recipient.id,
            actor_user_id=actor.id if actor else None,
            type=event_type,
            title=title,
            body=body,
            href=href,
            data_json=metadata or {},
        )
        db.session.add(notification)
        db.session.flush()

    if not email:
        return {"notification": notification, "email_log": None, "email_status": "disabled"}

    if suppress_self_email and actor and actor.id == recipient.id:
        return {
            "notification": notification,
            "email_log": _skip_email_log(
                notification=notification,
                recipient=recipient,
                event_type=event_type,
                related_type=related_type,
                related_id=related_id,
                dedupe_key=dedupe_key,
                reason="self email suppressed",
            ),
            "email_status": "skipped",
        }

    if not current_app.config.get("SEND_NOTIFICATION_EMAILS", True):
        return {
            "notification": notification,
            "email_log": _skip_email_log(
                notification=notification,
                recipient=recipient,
                event_type=event_type,
                related_type=related_type,
                related_id=related_id,
                dedupe_key=dedupe_key,
                reason="SEND_NOTIFICATION_EMAILS disabled",
            ),
            "email_status": "skipped",
        }

    if not recipient.is_active and not allow_inactive_email:
        return {
            "notification": notification,
            "email_log": _skip_email_log(
                notification=notification,
                recipient=recipient,
                event_type=event_type,
                related_type=related_type,
                related_id=related_id,
                dedupe_key=dedupe_key,
                reason="recipient inactive",
            ),
            "email_status": "skipped",
        }

    if not (recipient.email or "").strip():
        return {"notification": notification, "email_log": None, "email_status": "missing_email"}

    if not _email_allowed_by_preferences(recipient, email_category):
        return {
            "notification": notification,
            "email_log": _skip_email_log(
                notification=notification,
                recipient=recipient,
                event_type=event_type,
                related_type=related_type,
                related_id=related_id,
                dedupe_key=dedupe_key,
                reason="recipient email preferences disabled",
            ),
            "email_status": "skipped",
        }

    if _recent_email_sent(
        recipient=recipient,
        event_type=event_type,
        related_type=related_type,
        related_id=related_id,
        minutes=cooldown_minutes,
    ):
        return {
            "notification": notification,
            "email_log": _skip_email_log(
                notification=notification,
                recipient=recipient,
                event_type=event_type,
                related_type=related_type,
                related_id=related_id,
                dedupe_key=dedupe_key,
                reason="email cooldown",
            ),
            "email_status": "skipped",
        }

    from .email_service import EmailServiceError, send_notification_email

    try:
        result = send_notification_email(
            recipient,
            subject=title,
            heading=title,
            intro=body,
            action_url=_absolute_url(href),
            action_label=action_label,
            eyebrow="Progyx",
            details=details,
            metadata={
                "purpose": "notification",
                "event_type": event_type,
                "recipient_id": recipient.id,
                "notification_id": notification.id if notification else None,
                **(metadata or {}),
            },
        )
        status = "dry_run" if result.dry_run else ("skipped" if result.skipped else "sent")
        log = _upsert_email_log(
            notification=notification,
            recipient=recipient,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
            dedupe_key=dedupe_key,
            status=status,
            provider=result.provider,
            message_id=result.message_id,
        )
        return {"notification": notification, "email_log": log, "email_status": status}
    except EmailServiceError as exc:
        _log.warning(
            "notification_email_send_failed recipient_id=%s event_type=%s error=%s",
            recipient.id,
            event_type,
            exc,
        )
        log = _upsert_email_log(
            notification=notification,
            recipient=recipient,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
            dedupe_key=dedupe_key,
            status="failed",
            error=str(exc),
        )
        return {"notification": notification, "email_log": log, "email_status": "failed"}
    except Exception as exc:  # noqa: BLE001
        _log.exception(
            "notification_email_unexpected_failure recipient_id=%s event_type=%s",
            recipient.id,
            event_type,
        )
        log = _upsert_email_log(
            notification=notification,
            recipient=recipient,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
            dedupe_key=dedupe_key,
            status="failed",
            error=str(exc),
        )
        return {"notification": notification, "email_log": log, "email_status": "failed"}


def _active_staff() -> list[User]:
    return (
        User.query.filter(
            User.role.in_((UserRole.ADMIN, UserRole.SUPERADMIN)),
            User.is_active.is_(True),
        )
        .order_by(User.role.asc(), User.email.asc(), User.id.asc())
        .all()
    )


def notify_staff_teacher_application(teacher: User) -> None:
    for staff in _active_staff():
        notify_user(
            staff,
            event_type="teacher_application_created",
            title="Новая заявка учителя",
            body=f"{_display_name(teacher)} отправил(а) заявку на роль учителя.",
            href=_staff_href(staff, "/admin/teacher-requests"),
            actor=teacher,
            email_category=CATEGORY_STAFF,
            action_label="Открыть заявки",
            details=[
                ("Учитель", _display_name(teacher)),
                ("Email", teacher.email),
            ],
            related_type="teacher_request",
            related_id=teacher.id,
            dedupe_key=f"teacher_application_created:{teacher.id}:{staff.id}",
        )


def notify_teacher_request_decision(staff: User, teacher: User, *, approved: bool) -> None:
    if approved:
        title = "Заявка учителя одобрена"
        body = "Ваша заявка подтверждена. Теперь можно войти в кабинет учителя и работать с классами."
        action_label = "Открыть кабинет"
        href = "/teacher"
        status = "approved"
    else:
        title = "Заявка учителя отклонена"
        body = "Администратор отклонил заявку на роль учителя. Если это ошибка, обратитесь в поддержку."
        action_label = "Открыть поддержку"
        href = "/support"
        status = "rejected"
    notify_user(
        teacher,
        event_type="teacher_application_decision",
        title=title,
        body=body,
        href=href,
        actor=staff,
        email_category=CATEGORY_STAFF,
        action_label=action_label,
        details=[
            ("Статус", status),
            ("Email", teacher.email),
        ],
        related_type="teacher_request",
        related_id=teacher.id,
        dedupe_key=f"teacher_application_decision:{teacher.id}:{status}",
        allow_inactive_email=True,
    )


def notify_students_new_assignment(teacher: User, classroom: Classroom, assignment: Assignment) -> None:
    students = (
        User.query.join(ClassMembership, ClassMembership.student_id == User.id)
        .filter(
            ClassMembership.classroom_id == classroom.id,
            User.role == UserRole.STUDENT,
            User.is_active.is_(True),
        )
        .order_by(User.email.asc(), User.id.asc())
        .all()
    )
    href = f"/lessons/{assignment.lesson_id}" if assignment.lesson_id else "/dashboard"
    for student in students:
        notify_user(
            student,
            event_type="student_new_assignment",
            title="Новый урок от учителя",
            body=f"{_first_name(student)}, у вас появилось новое задание: «{assignment.title}».",
            href=href,
            actor=teacher,
            email_category=CATEGORY_ASSIGNMENTS,
            action_label="Открыть урок",
            details=[
                ("Класс", classroom.name),
                ("Учитель", _display_name(teacher)),
                ("Задание", assignment.title),
                ("Дедлайн", assignment.due_date or ""),
            ],
            related_type="assignment",
            related_id=assignment.id,
            dedupe_key=f"student_new_assignment:{assignment.id}:{student.id}",
        )


def notify_students_new_class_lesson(teacher: User, classroom: Classroom, lesson) -> None:
    students = (
        User.query.join(ClassMembership, ClassMembership.student_id == User.id)
        .filter(
            ClassMembership.classroom_id == classroom.id,
            User.role == UserRole.STUDENT,
            User.is_active.is_(True),
        )
        .order_by(User.email.asc(), User.id.asc())
        .all()
    )
    for student in students:
        notify_user(
            student,
            event_type="student_new_teacher_lesson",
            title="Новый урок от учителя",
            body=f"{_first_name(student)}, учитель добавил(а) новый урок: «{lesson.title}».",
            href=f"/lessons/{lesson.id}",
            actor=teacher,
            email_category=CATEGORY_ASSIGNMENTS,
            action_label="Открыть урок",
            details=[
                ("Класс", classroom.name),
                ("Учитель", _display_name(teacher)),
                ("Урок", lesson.title),
            ],
            related_type="lesson",
            related_id=lesson.id,
            dedupe_key=f"student_new_teacher_lesson:{lesson.id}:{student.id}",
        )


def notify_parent_child_achievement(parent: User, child: User, achievements: list) -> dict[str, Any]:
    capped = list(achievements[:5])
    if not capped:
        return {"email_status": "empty"}
    first = _first_name(child, "Ребёнок")
    names = ", ".join(str(getattr(item, "name", "") or "").strip() for item in capped if getattr(item, "name", None))
    subject = f"{first}: новое достижение"
    if len(capped) > 1:
        subject = f"{first}: новые достижения"
    codes = "-".join(str(getattr(item, "id", "") or getattr(item, "code", "")) for item in capped)
    share_text = (
        f"{first} получил(а) достижение в Progyx: {getattr(capped[0], 'name', 'новый шаг')}!"
    )
    return notify_user(
        parent,
        event_type="parent_child_achievement",
        title=subject,
        body=f"{first} получил(а) новое достижение в Progyx. Посмотрите прогресс и поддержите ребёнка.",
        href=f"/parent/dashboard?child={child.id}",
        actor=child,
        email_category=CATEGORY_PARENT_ACHIEVEMENTS,
        action_label="Посмотреть прогресс",
        details=[
            ("Ребёнок", _display_name(child, "Ребёнок")),
            ("Достижение", names),
            ("Поделитесь", share_text),
        ],
        metadata={"child_id": child.id, "achievement_count": len(achievements)},
        related_type="child_achievement",
        related_id=child.id,
        dedupe_key=f"parent_child_achievement:{parent.id}:{child.id}:{codes}",
    )


def notify_support_ticket_created(actor: User, ticket: SupportTicket) -> None:
    for staff in _active_staff():
        notify_user(
            staff,
            event_type="support_ticket_created",
            title="Новое обращение в поддержку",
            body=f"{_display_name(actor)} создал(а) обращение: «{ticket.subject}».",
            href=_staff_href(staff, f"/admin/support?ticket={ticket.id}"),
            actor=actor,
            email_category=CATEGORY_STAFF,
            action_label="Открыть обращение",
            details=[
                ("Автор", _display_name(actor)),
                ("Роль", actor.role.value),
                ("Категория", ticket.category),
                ("Тема", ticket.subject),
            ],
            related_type="support_ticket",
            related_id=ticket.id,
            dedupe_key=f"support_ticket_created:{ticket.id}:{staff.id}",
        )


def notify_support_ticket_message(sender: User, ticket: SupportTicket, message: SupportTicketMessage) -> None:
    if sender.role in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        owner = ticket.user
        if owner is None:
            return
        notify_user(
            owner,
            event_type="support_ticket_replied",
            title="Ответ в обращении",
            body=f"В обращении «{ticket.subject}» появился ответ от команды Progyx.",
            href=f"/support?ticket={ticket.id}",
            actor=sender,
            email_category=CATEGORY_MESSAGES,
            action_label="Открыть обращение",
            details=[
                ("Тема", ticket.subject),
                ("Сообщение", _preview(message.body)),
            ],
            related_type="support_ticket",
            related_id=ticket.id,
            dedupe_key=f"support_ticket_replied:{message.id}:{owner.id}",
        )
        return

    for staff in _active_staff():
        notify_user(
            staff,
            event_type="support_ticket_replied",
            title="Новое сообщение в обращении",
            body=f"{_display_name(sender)} написал(а) в обращении «{ticket.subject}».",
            href=_staff_href(staff, f"/admin/support?ticket={ticket.id}"),
            actor=sender,
            email_category=CATEGORY_STAFF,
            action_label="Открыть обращение",
            details=[
                ("Автор", _display_name(sender)),
                ("Тема", ticket.subject),
                ("Сообщение", _preview(message.body)),
            ],
            related_type="support_ticket",
            related_id=ticket.id,
            dedupe_key=f"support_ticket_message:{message.id}:{staff.id}",
        )


def notify_direct_message(
    *,
    sender: User,
    recipient: User,
    body: str,
    href: str,
    event_type: str,
    related_type: str,
    related_id: int,
    context: str,
) -> None:
    cooldown = max(int(current_app.config.get("MESSAGE_NOTIFICATION_EMAIL_COOLDOWN_MINUTES") or 15), 0)
    notify_user(
        recipient,
        event_type=event_type,
        title="Новое сообщение",
        body=f"{_display_name(sender)} написал(а): «{_preview(body, 90)}».",
        href=href,
        actor=sender,
        email_category=CATEGORY_MESSAGES,
        action_label="Открыть сообщения",
        details=[
            ("Раздел", context),
            ("Отправитель", _display_name(sender)),
        ],
        related_type=related_type,
        related_id=related_id,
        cooldown_minutes=cooldown,
    )


def notify_assignment_submission_teacher(student: User, assignment: Assignment, submission: AssignmentSubmission) -> None:
    classroom = assignment.classroom
    teacher = classroom.teacher if classroom else None
    if teacher is None:
        return
    notify_user(
        teacher,
        event_type="assignment_submission_pending_review",
        title="Ответ ждёт проверки",
        body=f"{_display_name(student)} отправил(а) ответ на задание «{assignment.title}».",
        href="/teacher#teacher-review",
        actor=student,
        email_category=CATEGORY_STAFF,
        action_label="Открыть проверку",
        details=[
            ("Класс", classroom.name if classroom else ""),
            ("Ученик", _display_name(student)),
            ("Задание", assignment.title),
        ],
        related_type="assignment_submission",
        related_id=submission.id,
        dedupe_key=f"assignment_submission_pending_review:{submission.id}:{teacher.id}:{submission.status}",
    )


def notify_teacher_class_join_request(student: User, classroom: Classroom, request_id: int) -> None:
    teacher = classroom.teacher
    if teacher is None:
        return
    notify_user(
        teacher,
        event_type="class_join_request_created",
        title="Новая заявка в класс",
        body=f"{_display_name(student)} хочет присоединиться к классу «{classroom.name}».",
        href="/teacher#teacher-classes",
        actor=student,
        email_category=CATEGORY_STAFF,
        action_label="Открыть заявки",
        details=[
            ("Класс", classroom.name),
            ("Ученик", _display_name(student)),
            ("Email", student.email),
        ],
        related_type="class_join_request",
        related_id=request_id,
        dedupe_key=f"class_join_request_created:{request_id}:{teacher.id}",
    )


def notify_parent_weekly_progress(parent: User, child: User, *, force: bool = False, now: datetime | None = None) -> dict[str, Any]:
    from . import parent_insights

    moment = now or _utcnow()
    iso = moment.date().isocalendar()
    dedupe_key = None if force else f"parent_weekly_progress:{parent.id}:{child.id}:{iso.year}-W{iso.week}"
    report = parent_insights.compact_progress_report(child)
    narrative = parent_insights.weekly_digest_narrative(child, allowed_module_slugs=None)
    minutes = parent_insights.learning_activity_estimate_minutes(child, allowed_module_slugs=None)
    trend = parent_insights.activity_trend_text(child, allowed_module_slugs=None)
    return notify_user(
        parent,
        event_type="parent_weekly_progress",
        title=f"Прогресс {_first_name(child, 'ребёнка')} за неделю",
        body=narrative,
        href=f"/parent/dashboard?child={child.id}",
        actor=child,
        email_category=CATEGORY_PARENT_WEEKLY_PROGRESS,
        action_label="Посмотреть прогресс",
        details=[
            ("Ребёнок", _display_name(child, "Ребёнок")),
            ("Уроков завершено", str(report["completed_lessons"])),
            ("Средний результат", f"{report['average_score']}%"),
            ("Заданий отправлено", str(report["tasks_submitted"])),
            ("Активность", f"{minutes} мин. за неделю"),
            ("Ритм", trend),
        ],
        metadata={"child_id": child.id, "week": f"{iso.year}-W{iso.week}"},
        related_type="parent_weekly_progress",
        related_id=child.id,
        dedupe_key=dedupe_key,
    )


def _parent_child_notifications_allowed(parent_id: int, child_id: int) -> bool:
    consent = ParentConsentSettings.query.filter_by(parent_user_id=parent_id, child_user_id=child_id).first()
    if consent and not consent.allow_notifications:
        return False
    return True


def run_weekly_parent_progress_reminders(*, force: bool = False, now: datetime | None = None) -> dict[str, int]:
    links = (
        ParentChildLink.query.filter_by(active=True)
        .filter(ParentChildLink.revoked_at.is_(None))
        .order_by(ParentChildLink.parent_user_id.asc(), ParentChildLink.child_user_id.asc())
        .all()
    )
    result = {"checked": 0, "sent": 0, "skipped": 0, "failed": 0}
    for link in links:
        result["checked"] += 1
        if not _parent_child_notifications_allowed(link.parent_user_id, link.child_user_id):
            result["skipped"] += 1
            continue
        parent = db.session.get(User, link.parent_user_id)
        child = db.session.get(User, link.child_user_id)
        if parent is None or child is None or not parent.is_active or not child.is_active:
            result["skipped"] += 1
            continue
        outcome = notify_parent_weekly_progress(parent, child, force=force, now=now)
        status = str(outcome.get("email_status") or "")
        if status in {"sent", "dry_run"}:
            result["sent"] += 1
        elif status == "failed":
            result["failed"] += 1
        else:
            result["skipped"] += 1
    return result
