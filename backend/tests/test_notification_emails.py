from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class _RecordingMailer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        text: str | None,
        metadata: dict | None,
    ):
        from app.services.email_service import EmailDeliveryResult

        self.calls.append(
            {
                "to": to,
                "subject": subject,
                "html": html,
                "text": text,
                "metadata": metadata,
            }
        )
        return EmailDeliveryResult(
            provider="unisender_go",
            accepted=True,
            message_id=f"notification-{len(self.calls)}",
        )


class NotificationEmailTests(unittest.TestCase):
    def setUp(self) -> None:
        self._apps = []
        self._tempdirs: list[tempfile.TemporaryDirectory[str]] = []
        self._mailer = _RecordingMailer()
        self._patcher = patch("app.services.email_service._send_via_unisender_go", new=self._mailer)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        for app in self._apps:
            with app.app_context():
                from app.core.db import db

                db.session.remove()
                db.engine.dispose()
        for tempdir in self._tempdirs:
            tempdir.cleanup()

    def create_app(self, **env_overrides):
        tempdir = tempfile.TemporaryDirectory()
        self._tempdirs.append(tempdir)
        database_path = Path(tempdir.name) / "notifications.db"
        env = {
            "APP_ENV": "development",
            "SECRET_KEY": "UnitTestSecretKey123!UnitTestSecretKey123!",
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "CLIENT_URL": "http://localhost:3000",
            "FRONTEND_PUBLIC_URL": "http://localhost:3000",
            "EMAIL_FROM": "no-reply@progyx.test",
            "EMAIL_FROM_NAME": "Progyx Test",
            "UNISENDER_GO_API_KEY": "test-api-key",
            "UNISENDER_GO_API_URL": "https://go1.unisender.example/ru/transactional/api/v1",
            "EMAIL_DRY_RUN": "false",
            "ENABLE_DEMO_DATA": "false",
            "SUPERADMIN_BOOTSTRAP": "false",
            "SESSION_COOKIE_SECURE": "false",
            "SESSION_COOKIE_SAMESITE": "Strict",
            "GIGACHAT_VERIFY_SSL": "true",
            "METRICS_DEBUG": "false",
            "THROTTLE_BACKEND": "db",
        }
        env.update(env_overrides)
        with patch.dict(os.environ, env, clear=False):
            import app.core.config as config_module
            import app as app_module

            importlib.reload(config_module)
            importlib.reload(app_module)
            app = app_module.create_app()
            app.config.update(TESTING=True)
            with app.app_context():
                from app.core.migrations import upgrade_database

                upgrade_database()
            self._apps.append(app)

        self._patcher.stop()
        self._patcher = patch("app.services.email_service._send_via_unisender_go", new=self._mailer)
        self._patcher.start()
        return app

    def create_user(self, app, *, email: str, password: str, role: str, full_name: str | None = None) -> int:
        from app.core.db import db
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        with app.app_context():
            user = User(
                full_name=full_name or email.split("@")[0],
                email=email,
                password_hash=hash_password(password),
                role=UserRole(role),
                age_group="middle" if role == "student" else None,
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    def login(self, client, login: str, password: str) -> None:
        response = client.post("/api/auth/login", json={"login": login, "password": password})
        self.assertEqual(response.status_code, 200, response.get_json())

    def create_assignment_fixture(self, app) -> dict[str, int]:
        from app.core.db import db
        from app.models.learning import ClassMembership, Classroom, Lesson, Module

        teacher_id = self.create_user(
            app,
            email="teacher-notify@example.com",
            password="TeacherPass123!",
            role="teacher",
            full_name="Teacher Notify",
        )
        student_id = self.create_user(
            app,
            email="student-notify@example.com",
            password="StudentPass123!",
            role="student",
            full_name="Student Notify",
        )
        with app.app_context():
            classroom = Classroom(
                name="Email Class",
                description="",
                code="EMAIL1",
                teacher_id=teacher_id,
            )
            module = Module(
                slug="email-module",
                title="Email Module",
                description="Module",
                age_group="middle",
                icon="book",
                color="#111827",
                order_index=1,
                is_published=True,
            )
            db.session.add_all([classroom, module])
            db.session.flush()
            lesson = Lesson(
                module_id=module.id,
                slug="email-lesson",
                title="Email Lesson",
                summary="Lesson summary",
                order_index=1,
                duration_minutes=10,
                passing_score=70,
                theory_blocks=[],
                interactive_steps=[],
            )
            db.session.add_all(
                [
                    lesson,
                    ClassMembership(classroom_id=classroom.id, student_id=student_id),
                ]
            )
            db.session.commit()
            return {
                "teacher_id": teacher_id,
                "student_id": student_id,
                "classroom_id": classroom.id,
                "lesson_id": lesson.id,
            }

    def test_student_receives_minimal_email_when_teacher_assigns_lesson(self):
        app = self.create_app()
        ids = self.create_assignment_fixture(app)

        with app.test_client() as client:
            self.login(client, "teacher-notify@example.com", "TeacherPass123!")
            response = client.post(
                f"/api/teacher/classes/{ids['classroom_id']}/assignments",
                json={
                    "title": "Новая практика",
                    "lesson_id": ids["lesson_id"],
                    "due_date": "2026-07-10",
                    "learning_goal": "Закрепить тему",
                    "resources": "Материалы урока",
                    "work_steps": "Открой урок\nВыполни практику",
                    "success_criteria": "Ответ отправлен",
                    "description": "Короткое задание по уроку",
                    "assignment_type": "lesson_practice",
                    "submission_format": "text",
                },
            )

        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(len(self._mailer.calls), 1)
        call = self._mailer.calls[0]
        self.assertEqual(call["to"], "student-notify@example.com")
        self.assertIn("Новый урок", call["subject"])
        self.assertIn("Открыть урок", call["html"])
        self.assertIn("http://localhost:3000/lessons/", call["html"])
        self.assertIn("background:#f9fafb", call["html"])

        with app.app_context():
            from app.models.notifications import EmailNotificationLog, UserNotification

            self.assertEqual(UserNotification.query.filter_by(type="student_new_assignment").count(), 1)
            log = EmailNotificationLog.query.filter_by(event_type="student_new_assignment").one()
            self.assertEqual(log.status, "sent")

    def test_weekly_parent_progress_email_has_direct_child_link_and_dedupes(self):
        app = self.create_app()
        parent_id = self.create_user(
            app,
            email="weekly-parent@example.com",
            password="ParentPass123!",
            role="parent",
            full_name="Weekly Parent",
        )
        child_id = self.create_user(
            app,
            email="weekly-child@example.com",
            password="StudentPass123!",
            role="student",
            full_name="Weekly Child",
        )
        with app.app_context():
            from app.core.db import db
            from app.models.parent_cabinet import ParentChildLink
            from app.services.notifications import run_weekly_parent_progress_reminders

            db.session.add(ParentChildLink(parent_user_id=parent_id, child_user_id=child_id))
            db.session.commit()

            first = run_weekly_parent_progress_reminders(now=datetime(2026, 7, 6, tzinfo=UTC))
            db.session.commit()
            second = run_weekly_parent_progress_reminders(now=datetime(2026, 7, 6, tzinfo=UTC))
            db.session.commit()

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(len(self._mailer.calls), 1)
        call = self._mailer.calls[0]
        self.assertEqual(call["to"], "weekly-parent@example.com")
        self.assertIn(f"http://localhost:3000/parent/dashboard?child={child_id}", call["html"])
        self.assertIn("Посмотреть прогресс", call["html"])

    def test_support_ticket_created_notifies_active_staff(self):
        app = self.create_app()
        self.create_user(app, email="support-user@example.com", password="StudentPass123!", role="student")
        self.create_user(app, email="support-admin@example.com", password="AdminPass123!", role="admin")

        with app.test_client() as client:
            self.login(client, "support-user@example.com", "StudentPass123!")
            response = client.post(
                "/api/support/tickets",
                json={
                    "category": "technical",
                    "subject": "Не открывается урок",
                    "description": "После входа вижу пустой экран.",
                },
            )

        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(len(self._mailer.calls), 1)
        call = self._mailer.calls[0]
        self.assertEqual(call["to"], "support-admin@example.com")
        self.assertIn("Новое обращение", call["subject"])
        self.assertIn("/admin/support", call["html"])

    def test_notification_preferences_can_disable_assignment_email(self):
        app = self.create_app()
        ids = self.create_assignment_fixture(app)

        with app.test_client() as student_client:
            self.login(student_client, "student-notify@example.com", "StudentPass123!")
            patched = student_client.patch(
                "/api/notifications/preferences",
                json={"email_assignments_enabled": False},
            )
            self.assertEqual(patched.status_code, 200, patched.get_json())

        self._mailer.calls.clear()
        with app.test_client() as teacher_client:
            self.login(teacher_client, "teacher-notify@example.com", "TeacherPass123!")
            response = teacher_client.post(
                f"/api/teacher/classes/{ids['classroom_id']}/assignments",
                json={
                    "title": "Практика без письма",
                    "lesson_id": ids["lesson_id"],
                    "due_date": "2026-07-11",
                    "learning_goal": "Закрепить тему",
                    "resources": "Материалы",
                    "work_steps": "Открой урок",
                    "success_criteria": "Ответ отправлен",
                    "description": "Задание",
                },
            )

        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(len(self._mailer.calls), 0)
        with app.app_context():
            from app.models.notifications import EmailNotificationLog

            log = EmailNotificationLog.query.filter_by(event_type="student_new_assignment").order_by(
                EmailNotificationLog.id.desc()
            ).first()
            self.assertIsNotNone(log)
            self.assertEqual(log.status, "skipped")
            self.assertIn("preferences", log.error)


if __name__ == "__main__":
    unittest.main()
