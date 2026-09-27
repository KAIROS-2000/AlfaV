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


class LessonAuthoringLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        database_path = Path(self.tempdir.name) / "authoring.db"
        env = {
            "APP_ENV": "development",
            "SECRET_KEY": "UnitTestSecretKey123!UnitTestSecretKey123!",
            "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
            "CLIENT_URL": "http://localhost:3000",
            "ENABLE_DEMO_DATA": "false",
            "SUPERADMIN_BOOTSTRAP": "false",
            "SESSION_COOKIE_SECURE": "false",
            "GIGACHAT_VERIFY_SSL": "true",
            "METRICS_DEBUG": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            import app.core.config as config_module
            import app as app_module

            importlib.reload(config_module)
            importlib.reload(app_module)
            self.app = app_module.create_app()
            self.app.config.update(TESTING=True)
            with self.app.app_context():
                from app import models  # noqa: F401
                from app.core.db import db
                from app.core.security import hash_password
                from app.models.learning import ClassMembership, Classroom, Module
                from app.models.user import User, UserRole

                db.create_all()
                admin = User(
                    full_name="Admin",
                    email="authoring-admin@example.com",
                    password_hash=hash_password("AdminPass123!"),
                    role=UserRole.ADMIN,
                    age_group="adult",
                )
                module = Module(
                    slug="authoring-module",
                    title="Authoring module",
                    description="draft lifecycle test",
                    age_group="middle",
                    order_index=1,
                    is_published=True,
                )
                teacher = User(
                    full_name="Teacher",
                    email="authoring-teacher@example.com",
                    password_hash=hash_password("TeacherPass123!"),
                    role=UserRole.TEACHER,
                    age_group="adult",
                )
                other_teacher = User(
                    full_name="Other teacher",
                    email="other-authoring-teacher@example.com",
                    password_hash=hash_password("OtherTeacherPass123!"),
                    role=UserRole.TEACHER,
                    age_group="adult",
                )
                student = User(
                    full_name="Student",
                    email="authoring-student@example.com",
                    password_hash=hash_password("StudentPass123!"),
                    role=UserRole.STUDENT,
                    age_group="middle",
                )
                db.session.add_all([admin, module, teacher, other_teacher, student])
                db.session.flush()
                classroom = Classroom(
                    name="Authoring class",
                    code="AUTHCLS",
                    teacher_id=teacher.id,
                )
                other_classroom = Classroom(
                    name="Other authoring class",
                    code="OTHRAUTH",
                    teacher_id=other_teacher.id,
                )
                db.session.add_all([classroom, other_classroom])
                db.session.flush()
                db.session.add(ClassMembership(classroom_id=classroom.id, student_id=student.id))
                db.session.commit()
                self.module_id = module.id
                self.classroom_id = classroom.id
                self.other_classroom_id = other_classroom.id

    def tearDown(self) -> None:
        with self.app.app_context():
            from app.core.db import db
            db.session.remove()
            db.engine.dispose()
        self.tempdir.cleanup()

    @staticmethod
    def _complete_teacher_payload(title: str = "Teacher lesson") -> dict:
        return {
            "title": title,
            "summary": "A complete class lesson.",
            "age_group": "middle",
            "duration_minutes": 30,
            "passing_score": 70,
            "content_format": "mixed",
            "theory_text": "A complete explanation.",
            "key_points": "First point\nSecond point",
            "interactive_steps": "Read the example\nTry the task",
            "practice_enabled": False,
            "quiz": {"enabled": False},
        }

    @staticmethod
    def _complete_admin_payload(title: str = "Admin lesson") -> dict:
        return {
            "title": title,
            "summary": "A complete roadmap lesson.",
            "content_format": "mixed",
            "duration_minutes": 30,
            "passing_score": 70,
            "theory_text": "A complete explanation.",
            "key_points": ["First point", "Second point"],
            "interactive_steps": ["Read the example", "Try the task"],
            "task": {"enabled": False},
            "quiz": {"enabled": False},
        }

    def test_draft_edit_conflict_publish_archive_and_full_duplicate(self):
        with self.app.test_client() as client:
            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-admin@example.com", "password": "AdminPass123!"}).status_code,
                200,
            )
            created = client.post(
                f"/api/admin/modules/{self.module_id}/lessons",
                json={
                    "title": "Draft lesson",
                    "summary": "A private lesson draft.",
                    "content_format": "practice",
                    "authoring_metadata": {"format_note": "Teacher note", "internal_only": "must be discarded"},
                    "theory_text": "Theory",
                    "key_points": ["One", "Two"],
                    "interactive_steps": ["Read", "Try"],
                    "task": {
                        "enabled": True,
                        "task_type": "code",
                        "title": "Print greeting",
                        "prompt": "Read stdin and print a greeting.",
                        "starter_code": "print('hello')",
                        "evaluation_mode": "stdin_stdout",
                        "tests": [{"input": "", "expected": "hello"}],
                    },
                    "quiz": {
                        "enabled": True,
                        "questions": [{
                            "type": "match",
                            "prompt": "Match values",
                            "left": ["one", "two"],
                            "right": ["1", "2"],
                            "correct": {"one": "1", "two": "2"},
                        }],
                    },
                },
            )
            self.assertEqual(created.status_code, 201)
            lesson = created.get_json()["lesson"]
            lesson_id = lesson["id"]
            self.assertEqual(lesson["status"], "draft")
            self.assertFalse(lesson["is_published"])
            self.assertEqual(lesson["authoring_metadata"], {"format_note": "Teacher note"})
            self.assertEqual(lesson["format_note"], "Teacher note")
            self.assertEqual(lesson["version"], 1)

            detail = client.get(f"/api/admin/lessons/{lesson_id}")
            self.assertEqual(detail.status_code, 200)
            authoring = detail.get_json()["lesson"]
            self.assertEqual(authoring["format_note"], "Teacher note")
            self.assertEqual(authoring["authoring_metadata"], {"format_note": "Teacher note"})
            self.assertEqual(authoring["tasks"][0]["validation"]["tests"][0]["input"], "")
            self.assertEqual(authoring["quizzes"][0]["questions"][0]["correct"], {"one": "1", "two": "2"})

            saved = client.patch(
                f"/api/admin/lessons/{lesson_id}",
                json={"version": authoring["version"], "title": "Edited draft", "format_note": "Updated note"},
            )
            self.assertEqual(saved.status_code, 200)
            saved_lesson = saved.get_json()["lesson"]
            self.assertEqual(saved_lesson["version"], authoring["version"] + 1)
            conflict = client.patch(f"/api/admin/lessons/{lesson_id}", json={"version": authoring["version"], "title": "Stale"})
            self.assertEqual(conflict.status_code, 409)

            published = client.post(
                f"/api/admin/lessons/{lesson_id}/publish",
                json={"version": saved_lesson["version"]},
            )
            self.assertEqual(published.status_code, 200)
            self.assertEqual(published.get_json()["lesson"]["status"], "published")
            with self.app.app_context():
                from app.core.db import db
                from app.models.learning import Assignment

                db.session.add(Assignment(
                    classroom_id=self.classroom_id,
                    lesson_id=lesson_id,
                    title="Dependent assignment",
                    description="Blocks archival",
                    difficulty="medium",
                    xp_reward=0,
                ))
                db.session.commit()
            blocked_archive = client.post(f"/api/admin/lessons/{lesson_id}/archive")
            self.assertEqual(blocked_archive.status_code, 409)
            self.assertEqual(blocked_archive.get_json()["dependencies"]["assignments"], 1)
            with self.app.app_context():
                from app.core.db import db
                from app.models.learning import Assignment

                Assignment.query.filter_by(lesson_id=lesson_id).delete()
                db.session.commit()
            self.assertEqual(client.post(f"/api/admin/lessons/{lesson_id}/archive").get_json()["lesson"]["status"], "archived")
            duplicate = client.post(f"/api/admin/lessons/{lesson_id}/duplicate")
            self.assertEqual(duplicate.status_code, 201)
            clone = duplicate.get_json()["lesson"]
            self.assertEqual(clone["status"], "draft")
            self.assertEqual(clone["tasks"][0]["validation"]["tests"][0]["expected"], "hello")
            self.assertEqual(clone["quizzes"][0]["questions"][0]["correct"], {"one": "1", "two": "2"})

    def test_teacher_save_is_silent_until_explicit_share(self):
        with self.app.test_client() as client:
            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-teacher@example.com", "password": "TeacherPass123!"}).status_code,
                200,
            )
            with patch("app.api.teacher.notifications.notify_students_new_class_lesson") as notify:
                created = client.post(
                    f"/api/teacher/classes/{self.classroom_id}/lessons",
                    json={
                        "title": "Teacher draft",
                        "summary": "Saved without notifying students.",
                        "age_group": "middle",
                        "duration_minutes": 30,
                        "passing_score": 70,
                        "content_format": "project",
                        "format_note": "Prepare materials first",
                        "theory_text": "Theory",
                        "key_points": "One\nTwo",
                        "interactive_steps": "Read\nTry",
                    },
                )
                self.assertEqual(created.status_code, 201)
                lesson = created.get_json()["lesson"]
                lesson_id = lesson["id"]
                self.assertFalse(lesson["is_published"])
                notify.assert_not_called()

                detail = client.get(f"/api/teacher/lessons/{lesson_id}")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.get_json()["lesson"]["format_note"], "Prepare materials first")
                shared = client.post(f"/api/teacher/lessons/{lesson_id}/share", json={"classroom_id": self.classroom_id})
                self.assertEqual(shared.status_code, 200)
                self.assertTrue(shared.get_json()["lesson"]["is_published"])
                notify.assert_called_once()

    def test_authoring_lists_save_incomplete_drafts_and_enforce_owner_scope(self):
        with self.app.test_client() as client:
            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-admin@example.com", "password": "AdminPass123!"}).status_code,
                200,
            )
            incomplete_normal = client.post(
                f"/api/admin/modules/{self.module_id}/lessons",
                json={"title": "Only a title", "summary": "Still incomplete"},
            )
            self.assertEqual(incomplete_normal.status_code, 400)

            saved_draft = client.post(
                f"/api/admin/modules/{self.module_id}/lessons",
                json={
                    "save_draft": True,
                    "draft_payload": {
                        "title": "",
                        "practice_enabled": True,
                        "task_title": "Partially written task",
                        "quiz": {"enabled": True, "questions": [{"type": "single", "prompt": ""}]},
                    },
                },
            )
            self.assertEqual(saved_draft.status_code, 201)
            admin_draft = saved_draft.get_json()["lesson"]
            self.assertEqual(admin_draft["status"], "draft")
            self.assertEqual(admin_draft["version"], 1)
            self.assertEqual(admin_draft["draft_payload"]["task_title"], "Partially written task")

            admin_drafts = client.get("/api/admin/lessons?status=draft")
            self.assertEqual(admin_drafts.status_code, 200)
            draft_card = next(item for item in admin_drafts.get_json()["lessons"] if item["id"] == admin_draft["id"])
            self.assertEqual(draft_card["status"], "draft")
            self.assertEqual(draft_card["module_id"], self.module_id)
            self.assertIn("updated_at", draft_card)
            self.assertIn("published_at", draft_card)
            self.assertEqual(draft_card["version"], 1)
            self.assertNotIn("draft_payload", draft_card)
            self.assertNotIn("authoring_metadata", draft_card)
            self.assertEqual(client.get("/api/admin/lessons?status=unknown").status_code, 400)

            blocked_publish = client.post(
                f"/api/admin/lessons/{admin_draft['id']}/publish",
                json={"version": admin_draft["version"]},
            )
            self.assertEqual(blocked_publish.status_code, 400)
            stale_publish = client.post(
                f"/api/admin/lessons/{admin_draft['id']}/publish",
                json={"version": 999},
            )
            self.assertEqual(stale_publish.status_code, 409)

            completed_payload = self._complete_admin_payload("Ready admin lesson")
            completed_payload["version"] = admin_draft["version"]
            completed = client.patch(
                f"/api/admin/lessons/{admin_draft['id']}",
                json=completed_payload,
            )
            self.assertEqual(completed.status_code, 200)
            ready_admin = completed.get_json()["lesson"]
            self.assertIsNone(ready_admin["draft_payload"])
            published = client.post(
                f"/api/admin/lessons/{admin_draft['id']}/publish",
                json={"version": ready_admin["version"]},
            )
            self.assertEqual(published.status_code, 200)
            published_admin = published.get_json()["lesson"]
            self.assertEqual(published_admin["status"], "published")
            self.assertTrue(published_admin["published_at"])
            published_list = client.get("/api/admin/lessons?status=published")
            self.assertIn(admin_draft["id"], {item["id"] for item in published_list.get_json()["lessons"]})

            archived = client.post(
                f"/api/admin/lessons/{admin_draft['id']}/archive",
                json={"version": published_admin["version"]},
            )
            self.assertEqual(archived.status_code, 200)
            archived_list = client.get("/api/admin/lessons?status=archived")
            self.assertIn(admin_draft["id"], {item["id"] for item in archived_list.get_json()["lessons"]})

            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-teacher@example.com", "password": "TeacherPass123!"}).status_code,
                200,
            )
            self.assertEqual(
                client.post(f"/api/teacher/classes/{self.classroom_id}/lessons", json={}).status_code,
                400,
            )
            teacher_draft_response = client.post(
                f"/api/teacher/classes/{self.classroom_id}/lessons",
                json={
                    "save_draft": True,
                    "draft_payload": {"title": "Teacher partial", "quiz": {"enabled": True}},
                },
            )
            self.assertEqual(teacher_draft_response.status_code, 201)
            teacher_draft = teacher_draft_response.get_json()["lesson"]
            teacher_list = client.get(f"/api/teacher/classes/{self.classroom_id}/lessons?status=draft")
            self.assertEqual(teacher_list.status_code, 200)
            teacher_card = next(item for item in teacher_list.get_json()["lessons"] if item["id"] == teacher_draft["id"])
            self.assertEqual(teacher_card["classroom_id"], self.classroom_id)
            self.assertEqual(teacher_card["classroom_name"], "Authoring class")
            self.assertEqual(teacher_card["status"], "draft")
            self.assertEqual(
                client.get(f"/api/teacher/classes/{self.other_classroom_id}/lessons").status_code,
                404,
            )

            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-admin@example.com", "password": "AdminPass123!"}).status_code,
                200,
            )
            all_admin_lessons = client.get("/api/admin/lessons?status=all")
            self.assertEqual(all_admin_lessons.status_code, 200)
            self.assertNotIn(teacher_draft["id"], {item["id"] for item in all_admin_lessons.get_json()["lessons"]})

    def test_teacher_builder_patch_and_student_visibility_boundary(self):
        with self.app.test_client() as client:
            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-teacher@example.com", "password": "TeacherPass123!"}).status_code,
                200,
            )
            created = client.post(
                f"/api/teacher/classes/{self.classroom_id}/lessons",
                json=self._complete_teacher_payload("Private teacher lesson"),
            )
            self.assertEqual(created.status_code, 201)
            private_lesson = created.get_json()["lesson"]
            lesson_id = private_lesson["id"]
            module_id = private_lesson["module"]["id"]

            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-student@example.com", "password": "StudentPass123!"}).status_code,
                200,
            )
            self.assertEqual(client.get(f"/api/lessons/{lesson_id}").status_code, 403)
            hidden_list = client.get(f"/api/modules/{module_id}/lessons")
            self.assertEqual(hidden_list.status_code, 200)
            self.assertNotIn(lesson_id, {item["id"] for item in hidden_list.get_json()["lessons"]})

            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-teacher@example.com", "password": "TeacherPass123!"}).status_code,
                200,
            )
            detail = client.get(f"/api/teacher/lessons/{lesson_id}")
            self.assertEqual(detail.status_code, 200)
            version = detail.get_json()["lesson"]["version"]
            builder_patch = {
                "version": version,
                "title": "Edited teacher lesson",
                "summary": "Updated from the shared builder shape.",
                "content_format": "practice",
                "authoring_metadata": {"format_note": "Edit note"},
                "duration_minutes": 45,
                "passing_score": 80,
                "theory_text": "Updated theory text.",
                "key_points": "Updated point one\nUpdated point two",
                "interactive_steps": "Inspect the example\nWrite an answer",
                "task": {
                    "enabled": True,
                    "task_type": "text",
                    "title": "Explain the result",
                    "prompt": "Use both updated points in the answer.",
                    "evaluation_mode": "keywords",
                    "keywords": "updated,answer",
                    "hints": ["Use the theory."],
                },
                "quiz": {
                    "enabled": True,
                    "title": "Updated quiz",
                    "passing_score": 70,
                    "questions": [{
                        "type": "text",
                        "prompt": "What should the learner do?",
                        "correct": ["answer"],
                    }],
                },
            }
            updated = client.patch(f"/api/teacher/lessons/{lesson_id}", json=builder_patch)
            self.assertEqual(updated.status_code, 200)
            updated_lesson = updated.get_json()["lesson"]
            self.assertEqual(updated_lesson["theory_blocks"][1]["text"], "Updated theory text.")
            self.assertEqual(updated_lesson["tasks"][0]["title"], "Explain the result")
            self.assertEqual(updated_lesson["tasks"][0]["validation"]["keywords"], ["updated", "answer"])
            self.assertEqual(updated_lesson["quizzes"][0]["title"], "Updated quiz")

            with patch("app.api.teacher.notifications.notify_students_new_class_lesson") as notify:
                shared = client.post(
                    f"/api/teacher/lessons/{lesson_id}/share",
                    json={"classroom_id": self.classroom_id, "version": updated_lesson["version"]},
                )
                self.assertEqual(shared.status_code, 200)
                shared_lesson = shared.get_json()["lesson"]
                notify.assert_called_once()
                repeated_share = client.post(
                    f"/api/teacher/lessons/{lesson_id}/share",
                    json={"classroom_id": self.classroom_id, "version": shared_lesson["version"]},
                )
                self.assertEqual(repeated_share.status_code, 200)
                notify.assert_called_once()

            self.assertEqual(
                client.patch(
                    f"/api/teacher/lessons/{lesson_id}",
                    json={"version": shared_lesson["version"], "save_draft": True, "draft_payload": {"title": "unsafe"}},
                ).status_code,
                409,
            )

            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-student@example.com", "password": "StudentPass123!"}).status_code,
                200,
            )
            self.assertEqual(client.get(f"/api/lessons/{lesson_id}").status_code, 200)
            visible_list = client.get(f"/api/modules/{module_id}/lessons")
            self.assertIn(lesson_id, {item["id"] for item in visible_list.get_json()["lessons"]})

            with self.app.app_context():
                from app.core.db import db
                from app.models.learning import Lesson

                lesson = db.session.get(Lesson, lesson_id)
                lesson.is_published = False
                lesson.archived_at = datetime.now(UTC)
                db.session.commit()

            self.assertEqual(client.get(f"/api/lessons/{lesson_id}").status_code, 403)
            archived_list = client.get(f"/api/modules/{module_id}/lessons")
            self.assertNotIn(lesson_id, {item["id"] for item in archived_list.get_json()["lessons"]})

    def test_versioned_mapper_rejects_concurrent_authoring_writes(self):
        with self.app.test_client() as client:
            self.assertEqual(
                client.post("/api/auth/login", json={"login": "authoring-admin@example.com", "password": "AdminPass123!"}).status_code,
                200,
            )
            created = client.post(
                f"/api/admin/modules/{self.module_id}/lessons",
                json=self._complete_admin_payload("Versioned lesson"),
            )
            self.assertEqual(created.status_code, 201)
            lesson_id = created.get_json()["lesson"]["id"]

        with self.app.app_context():
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.orm.exc import StaleDataError

            from app.core.db import db
            from app.models.learning import Lesson

            session_factory = sessionmaker(bind=db.engine)
            first_session = session_factory()
            second_session = session_factory()
            try:
                first_lesson = first_session.get(Lesson, lesson_id)
                second_lesson = second_session.get(Lesson, lesson_id)
                first_lesson.title = "First writer"
                first_lesson.version += 1
                first_session.commit()

                second_lesson.title = "Second writer"
                second_lesson.version += 1
                with self.assertRaises(StaleDataError):
                    second_session.commit()
                second_session.rollback()
            finally:
                first_session.close()
                second_session.close()

    def test_authoring_lists_paginate_before_visibility_filtering(self):
        with self.app.app_context():
            from app.core.db import db
            from app.models.learning import Lesson, Module, build_custom_classroom_module_slug

            roadmap_module = db.session.get(Module, self.module_id)
            teacher_module = Module(
                slug=build_custom_classroom_module_slug(self.classroom_id, "middle"),
                title="Teacher module",
                description="Owned lessons",
                age_group="middle",
                order_index=100,
                is_published=False,
            )
            foreign_module = Module(
                slug=build_custom_classroom_module_slug(self.other_classroom_id, "middle"),
                title="Foreign teacher module",
                description="Foreign lessons",
                age_group="middle",
                order_index=101,
                is_published=False,
            )
            extra_roadmap_modules = [
                Module(
                    slug=f"roadmap-page-{index}",
                    title=f"Roadmap page {index}",
                    description="Pagination module",
                    age_group="middle",
                    order_index=index + 1,
                    is_published=True,
                )
                for index in range(20)
            ]
            db.session.add_all([teacher_module, foreign_module, *extra_roadmap_modules])
            db.session.flush()

            def lesson(module, index, *, published=False):
                return Lesson(
                    module_id=module.id,
                    slug=f"{module.slug}-lesson-{index}",
                    title=f"{module.title} lesson {index}",
                    summary="Pagination lesson",
                    theory_blocks=[],
                    interactive_steps=[],
                    order_index=index,
                    duration_minutes=20,
                    passing_score=70,
                    is_published=published,
                )

            roadmap_lessons = [lesson(roadmap_module, index) for index in range(1, 21)]
            teacher_lessons = [lesson(teacher_module, index, published=True) for index in range(1, 21)]
            foreign_lessons = [lesson(foreign_module, index, published=True) for index in range(1, 5)]
            db.session.add_all([*roadmap_lessons, *teacher_lessons, *foreign_lessons])
            db.session.commit()

        with self.app.test_client() as client:
            self.assertEqual(
                client.post(
                    "/api/auth/login",
                    json={"login": "authoring-admin@example.com", "password": "AdminPass123!"},
                ).status_code,
                200,
            )
            first = client.get("/api/admin/lessons?status=all&page_size=99").get_json()
            second = client.get("/api/admin/lessons?status=all&page=2&page_size=15").get_json()
            self.assertEqual(len(first["lessons"]), 15)
            self.assertEqual(first["pagination"], {"page": 1, "page_size": 15, "total": 20, "total_pages": 2})
            self.assertEqual(len(second["lessons"]), 5)
            self.assertTrue(
                {item["id"] for item in first["lessons"]}.isdisjoint(
                    {item["id"] for item in second["lessons"]}
                )
            )

            modules = client.get("/api/admin/modules?page_size=100").get_json()
            self.assertEqual(len(modules["modules"]), 15)
            self.assertEqual(modules["pagination"]["total"], 21)
            self.assertEqual(modules["stats"], {"total": 21, "published": 21})
            self.assertTrue(all(not item["is_custom_classroom_module"] for item in modules["modules"]))
            self.assertTrue(all("lessons" not in item for item in modules["modules"]))
            roadmap_summary = next(item for item in modules["modules"] if item["id"] == self.module_id)
            self.assertEqual(roadmap_summary["lessons_count"], 20)

            self.assertEqual(
                client.post(
                    "/api/auth/login",
                    json={"login": "authoring-teacher@example.com", "password": "TeacherPass123!"},
                ).status_code,
                200,
            )
            owned = client.get(
                f"/api/teacher/classes/{self.classroom_id}/lessons?status=all&page_size=100"
            ).get_json()
            self.assertEqual(len(owned["lessons"]), 15)
            self.assertEqual(owned["pagination"]["total"], 20)
            self.assertTrue(all(item["classroom_id"] == self.classroom_id for item in owned["lessons"]))

            found = client.get(
                f"/api/teacher/lesson-catalog?classroom_id={self.classroom_id}"
                "&source=teacher&q=lesson%2020"
            ).get_json()
            self.assertEqual(found["pagination"]["total"], 1)
            self.assertEqual(found["lessons"][0]["title"], "Teacher module lesson 20")
