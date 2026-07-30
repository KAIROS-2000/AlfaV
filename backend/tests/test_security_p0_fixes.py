"""Regression tests for P0 security fixes.

Each test pins a specific anti-cheat / authorization invariant introduced when
closing the audit's CRITICAL findings (C-01..C-07, S-06, S-11, S-13, S-18).
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


_PROD_REDIS_ENV = {
    'REDIS_URL': 'redis://127.0.0.1:6379/0',
    'REDIS_PASSWORD': 'UnitTestRedisPassword0123456789ABC!',
}


class P0FixesBase(unittest.TestCase):
    def setUp(self) -> None:
        self._apps = []
        self._tempdirs: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self) -> None:
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
        database_path = Path(tempdir.name) / 'test.db'
        env = {
            'APP_ENV': 'development',
            'SECRET_KEY': 'UnitTestSecretKey123!UnitTestSecretKey123!',
            'DATABASE_URL': f'sqlite:///{database_path.as_posix()}',
            'CLIENT_URL': 'http://localhost:3000',
            'ENABLE_DEMO_DATA': 'false',
            'SUPERADMIN_BOOTSTRAP': 'false',
            'SESSION_COOKIE_SECURE': 'false',
            'SESSION_COOKIE_SAMESITE': 'Strict',
            'GIGACHAT_VERIFY_SSL': 'true',
            'CODE_JUDGE_RUNNER_URL': '',
            'CODE_JUDGE_RUNNER_TOKEN': '',
            'METRICS_DEBUG': 'false',
            'TRUST_PROXY': 'false',
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
                from app.core.db import db
                from app.core.runtime_schema import ensure_runtime_schema

                db.create_all()
                ensure_runtime_schema()
            self._apps.append(app)
            return app

    # ---- fixture builders ---------------------------------------------------

    def _make_module_with_lesson(
        self,
        app,
        *,
        slug_suffix: str,
        with_task: bool = False,
        with_quiz: bool = False,
        passing_score: int = 70,
    ):
        """Builds an isolated module + first lesson so tests are not affected by seed ordering."""
        from app.core.db import db
        from app.models.learning import Lesson, Module, Quiz, Task

        with app.app_context():
            module = Module(
                slug=f'p0-fix-mod-{slug_suffix}',
                title=f'P0 Fix Module {slug_suffix}',
                description='isolated test fixture',
                age_group='middle',
                icon='code',
                color='#4A90D9',
                order_index=900 + (hash(slug_suffix) & 0xff),
                is_published=True,
            )
            db.session.add(module)
            db.session.flush()
            lesson = Lesson(
                module_id=module.id,
                slug=f'p0-fix-lesson-{slug_suffix}',
                title='Test lesson',
                summary='isolated',
                order_index=1,
                passing_score=passing_score,
                theory_blocks=[],
                interactive_steps=[],
                is_published=True,
            )
            db.session.add(lesson)
            db.session.flush()
            task_id = None
            quiz_id = None
            if with_task:
                task = Task(
                    lesson_id=lesson.id,
                    task_type='text',
                    title='Practice',
                    prompt='Solve this',
                    starter_code='',
                    validation={
                        'evaluation_mode': 'manual',
                        'language': None,
                        'keywords': [],
                        'tests': [],
                    },
                    hints=[],
                    xp_reward=10,
                )
                db.session.add(task)
                db.session.flush()
                task_id = task.id
            if with_quiz:
                quiz = Quiz(
                    lesson_id=lesson.id,
                    title='Test quiz',
                    passing_score=passing_score,
                    questions=[
                        {
                            'id': 'q1',
                            'type': 'single',
                            'prompt': 'Pick',
                            'options': [{'id': 'a', 'text': 'A'}, {'id': 'b', 'text': 'B'}],
                            'correct': 'a',
                        }
                    ],
                    xp_reward=20,
                )
                db.session.add(quiz)
                db.session.flush()
                quiz_id = quiz.id
            db.session.commit()
            return {
                'module_id': module.id,
                'lesson_id': lesson.id,
                'task_id': task_id,
                'quiz_id': quiz_id,
            }

    def create_user(self, app, *, role, email, password='StrongPass123!', age_group='middle'):
        from app.core.db import db
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        # ADMIN/SUPERADMIN/PARENT do not have a learner age_group; flatten for those roles.
        if role in (UserRole.ADMIN, UserRole.SUPERADMIN, UserRole.PARENT, UserRole.TEACHER):
            stored_age_group = None
        else:
            stored_age_group = age_group

        with app.app_context():
            user = User(
                full_name=f'{role.value.title()} User',
                email=email,
                password_hash=hash_password(password),
                role=role,
                age_group=stored_age_group,
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    def create_student(self, app, *, email='student@example.com', password='StrongPass123!', age_group='middle'):
        from app.models.user import UserRole

        return self.create_user(app, role=UserRole.STUDENT, email=email, password=password, age_group=age_group)

    def login(self, client, email='student@example.com', password='StrongPass123!'):
        return client.post('/api/auth/login', json={'login': email, 'password': password})


# =====================================================================================
# C-01: anti-cheat for completion_percent
# =====================================================================================


class CompletionPercentAntiCheatTests(P0FixesBase):
    def test_complete_lesson_ignores_client_completion_percent_when_practice_not_solved(self):
        app = self.create_app()
        ids = self._make_module_with_lesson(app, slug_suffix='cheat', with_task=True)
        self.create_student(app)

        with app.test_client() as client:
            self.login(client)
            response = client.patch(
                f"/api/lessons/{ids['lesson_id']}/complete",
                json={'completion_percent': 100, 'answer': 'fake'},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        # progress.score is 0 because no submit_task happened — server must NOT trust the client value.
        self.assertEqual(payload['progress']['score'], 0)
        self.assertNotEqual(payload['progress']['status'], 'completed')

    def test_complete_lesson_for_theory_only_lesson_marks_completed(self):
        """Lessons with no tasks/quizzes legitimately complete on patch — there's nothing to fake."""
        app = self.create_app()
        ids = self._make_module_with_lesson(app, slug_suffix='theory', with_task=False, with_quiz=False)
        self.create_student(app)

        with app.test_client() as client:
            self.login(client)
            response = client.patch(f"/api/lessons/{ids['lesson_id']}/complete", json={})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['progress']['score'], 100)
        self.assertEqual(payload['progress']['status'], 'completed')


# =====================================================================================
# C-02: role-restricted endpoints (lesson flows vs student-only utilities)
# =====================================================================================


class RoleRestrictedSubmissionTests(P0FixesBase):
    def test_admin_submit_task_updates_progress_without_lesson_xp(self):
        """Staff may practice tasks; XP from lesson flows remains student-only."""
        app = self.create_app()
        from app.models.user import UserRole

        ids = self._make_module_with_lesson(app, slug_suffix='admsubmit', with_task=True)
        self.create_user(app, role=UserRole.ADMIN, email='admin@example.com')

        with app.test_client() as client:
            self.login(client, email='admin@example.com')
            response = client.post(
                f"/api/tasks/{ids['task_id']}/submit",
                json={'answer': 'whatever'},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('xp_awarded'), 0)
        self.assertFalse(payload.get('xp_skipped'))
        self.assertIn('progress', payload)

    def test_teacher_submit_quiz_updates_progress_without_lesson_xp(self):
        app = self.create_app()
        from app.models.user import UserRole

        ids = self._make_module_with_lesson(app, slug_suffix='tchquiz', with_quiz=True)
        self.create_user(app, role=UserRole.TEACHER, email='teacher@example.com')

        with app.test_client() as client:
            self.login(client, email='teacher@example.com')
            response = client.post(
                f"/api/quizzes/{ids['quiz_id']}/submit",
                json={'answers': {'q1': 'a'}},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload.get('xp_awarded'), 0)
        self.assertFalse(payload.get('xp_skipped'))
        self.assertIn('progress', payload)

    def test_parent_can_complete_theory_lesson(self):
        app = self.create_app()
        from app.models.user import UserRole

        ids = self._make_module_with_lesson(app, slug_suffix='parent', with_task=False)
        self.create_user(app, role=UserRole.PARENT, email='parent@example.com')

        with app.test_client() as client:
            self.login(client, email='parent@example.com')
            response = client.patch(f"/api/lessons/{ids['lesson_id']}/complete", json={})

        self.assertEqual(response.status_code, 200)

    def test_parent_can_start_lesson(self):
        app = self.create_app()
        from app.models.user import UserRole

        ids = self._make_module_with_lesson(app, slug_suffix='parentstart', with_task=False)
        self.create_user(app, role=UserRole.PARENT, email='parent@example.com')

        with app.test_client() as client:
            self.login(client, email='parent@example.com')
            response = client.post(f"/api/lessons/{ids['lesson_id']}/start")

        self.assertEqual(response.status_code, 200)


# =====================================================================================
# Curriculum access and private judge-output regressions
# =====================================================================================


class CurriculumAccessControlTests(P0FixesBase):
    def _create_visibility_fixture(self, app, *, teacher_id: int, member_id: int):
        from app.core.db import db
        from app.models.learning import (
            ClassMembership,
            Classroom,
            Lesson,
            Module,
            build_custom_classroom_module_slug,
        )

        with app.app_context():
            public_module = Module(
                slug='visibility-public',
                title='Public module',
                description='Published module with a draft sibling.',
                age_group='middle',
                icon='code',
                color='#4A90D9',
                order_index=1,
                is_published=True,
            )
            private_module = Module(
                slug='visibility-private',
                title='Private module',
                description='Unpublished global module.',
                age_group='middle',
                icon='code',
                color='#4A90D9',
                order_index=2,
                is_published=False,
            )
            classroom = Classroom(
                name='Visibility class',
                description='Authorization fixture',
                code='VIS001',
                teacher_id=teacher_id,
            )
            db.session.add_all([public_module, private_module, classroom])
            db.session.flush()
            custom_module = Module(
                slug=build_custom_classroom_module_slug(classroom.id, 'middle'),
                title='Class-only module',
                description='Only classroom members may open this module.',
                age_group='middle',
                icon='book-open',
                color='#0EA5E9',
                order_index=3,
                # A mistaken publish flag must never make class content public.
                is_published=True,
            )
            db.session.add(custom_module)
            db.session.flush()
            public_lesson = Lesson(
                module_id=public_module.id,
                slug='visibility-public-lesson',
                title='Public lesson',
                summary='Visible',
                order_index=1,
                passing_score=70,
                theory_blocks=[],
                interactive_steps=[],
                is_published=True,
            )
            draft_lesson = Lesson(
                module_id=public_module.id,
                slug='visibility-draft-lesson',
                title='Draft lesson',
                summary='Must not leak',
                order_index=2,
                passing_score=70,
                theory_blocks=[],
                interactive_steps=[],
                is_published=False,
            )
            private_lesson = Lesson(
                module_id=private_module.id,
                slug='visibility-private-lesson',
                title='Private lesson',
                summary='Must not leak',
                order_index=1,
                passing_score=70,
                theory_blocks=[],
                interactive_steps=[],
                is_published=False,
            )
            custom_lesson = Lesson(
                module_id=custom_module.id,
                slug='visibility-class-lesson',
                title='Class lesson',
                summary='Visible to its class only',
                order_index=1,
                passing_score=70,
                theory_blocks=[],
                interactive_steps=[],
                is_published=False,
            )
            db.session.add_all(
                [public_lesson, draft_lesson, private_lesson, custom_lesson]
            )
            db.session.add(
                ClassMembership(classroom_id=classroom.id, student_id=member_id)
            )
            db.session.commit()
            return {
                'public_module_id': public_module.id,
                'public_lesson_id': public_lesson.id,
                'draft_lesson_id': draft_lesson.id,
                'private_lesson_id': private_lesson.id,
                'custom_module_id': custom_module.id,
                'custom_lesson_id': custom_lesson.id,
            }

    def test_curriculum_access_is_explicit_for_drafts_classes_and_managers(self):
        app = self.create_app()
        from app.models.user import UserRole

        teacher_id = self.create_user(
            app, role=UserRole.TEACHER, email='visibility-teacher@example.com'
        )
        member_id = self.create_student(app, email='visibility-member@example.com')
        self.create_student(app, email='visibility-outsider@example.com')
        self.create_user(app, role=UserRole.PARENT, email='visibility-parent@example.com')
        self.create_user(app, role=UserRole.MANAGER, email='visibility-manager@example.com')
        self.create_user(app, role=UserRole.ADMIN, email='visibility-admin@example.com')
        ids = self._create_visibility_fixture(
            app, teacher_id=teacher_id, member_id=member_id
        )

        with app.test_client() as public_client:
            bootstrap = public_client.get('/api/bootstrap')
        self.assertEqual(bootstrap.status_code, 200)
        self.assertNotIn(
            ids['custom_module_id'],
            [module['id'] for module in bootstrap.get_json()['featured_modules']],
        )
        public_module = next(
            module
            for module in bootstrap.get_json()['featured_modules']
            if module['id'] == ids['public_module_id']
        )
        self.assertEqual(
            [lesson['id'] for lesson in public_module['lessons']],
            [ids['public_lesson_id']],
        )

        with app.test_client() as manager_client:
            self.login(manager_client, email='visibility-manager@example.com')
            catalog = manager_client.get('/api/modules?age_group=middle')
            self.assertEqual(catalog.status_code, 200)
            self.assertNotIn(
                ids['public_module_id'],
                [module['id'] for module in catalog.get_json()['modules']],
            )
            self.assertEqual(
                manager_client.get(
                    f"/api/lessons/{ids['public_lesson_id']}"
                ).status_code,
                403,
            )
            self.assertEqual(
                manager_client.get(
                    f"/api/modules/{ids['custom_module_id']}/lessons"
                ).status_code,
                403,
            )
            self.assertEqual(
                manager_client.post(
                    f"/api/lessons/{ids['public_lesson_id']}/start"
                ).status_code,
                403,
            )

        with app.test_client() as parent_client:
            self.login(parent_client, email='visibility-parent@example.com')
            self.assertEqual(
                parent_client.get(
                    f"/api/lessons/{ids['private_lesson_id']}"
                ).status_code,
                403,
            )

        with app.test_client() as outsider_client:
            self.login(outsider_client, email='visibility-outsider@example.com')
            self.assertEqual(
                outsider_client.get(
                    f"/api/lessons/{ids['custom_lesson_id']}"
                ).status_code,
                403,
            )

        with app.test_client() as member_client:
            self.login(member_client, email='visibility-member@example.com')
            member_lesson = member_client.get(
                f"/api/lessons/{ids['public_lesson_id']}"
            )
            self.assertEqual(member_lesson.status_code, 200)
            self.assertEqual(
                [
                    lesson['id']
                    for lesson in member_lesson.get_json()['lesson']['module']['lessons']
                ],
                [ids['public_lesson_id']],
            )
            self.assertEqual(
                member_client.get(
                    f"/api/lessons/{ids['custom_lesson_id']}"
                ).status_code,
                200,
            )

        with app.test_client() as teacher_client:
            self.login(teacher_client, email='visibility-teacher@example.com')
            self.assertEqual(
                teacher_client.get(
                    f"/api/lessons/{ids['custom_lesson_id']}"
                ).status_code,
                200,
            )

        with app.test_client() as admin_client:
            self.login(admin_client, email='visibility-admin@example.com')
            self.assertEqual(
                admin_client.get(
                    f"/api/lessons/{ids['private_lesson_id']}"
                ).status_code,
                200,
            )


class JudgeResultPrivacyTests(P0FixesBase):
    def _create_code_task(self, app) -> int:
        from app.core.db import db
        from app.models.learning import Task

        ids = self._make_module_with_lesson(app, slug_suffix='judge-private')
        with app.app_context():
            task = Task(
                lesson_id=ids['lesson_id'],
                task_type='code',
                title='Private judge task',
                prompt='Print the supplied input.',
                starter_code='print(input())',
                validation={
                    'evaluation_mode': 'stdin_stdout',
                    'language': 'python',
                    'tests': [
                        {
                            'label': 'private case',
                            'input': 'PRIVATE_TEST_INPUT',
                            'expected': 'PRIVATE_TEST_EXPECTED',
                        }
                    ],
                },
                hints=[],
                xp_reward=10,
            )
            db.session.add(task)
            db.session.commit()
            return task.id

    def test_task_submission_returns_only_aggregate_judge_feedback(self):
        app = self.create_app()
        task_id = self._create_code_task(app)
        self.create_student(app)
        private_report = {
            'mode': 'stdin_stdout',
            'runner': 'stdin_stdout',
            'language': 'python',
            'passed': False,
            'score': 0,
            'feedback': 'PRIVATE_FEEDBACK_MARKER',
            'tests_passed': 0,
            'tests_total': 1,
            'results': [
                {
                    'label': 'PRIVATE_TEST_LABEL',
                    'input': 'PRIVATE_TEST_INPUT',
                    'expected': 'PRIVATE_TEST_EXPECTED',
                    'actual': 'PRIVATE_TEST_ACTUAL',
                    'stderr': 'PRIVATE_TEST_STDERR',
                    'passed': False,
                    'duration_ms': 7,
                    'error_type': 'runtime_error',
                }
            ],
            'compile_error': 'PRIVATE_TEST_COMPILE_ERROR',
            'runtime_error': 'PRIVATE_TEST_RUNTIME_ERROR',
            'time_limit_ms': 2000,
            'memory_limit_mb': 128,
        }

        with app.test_client() as client, patch(
            'app.api.student.judge_task_submission', return_value=private_report
        ):
            self.login(client)
            response = client.post(
                f'/api/tasks/{task_id}/submit', json={'answer': 'print(input())'}
            )

        self.assertEqual(response.status_code, 200)
        raw_response = response.get_data(as_text=True)
        for secret in (
            'PRIVATE_FEEDBACK_MARKER',
            'PRIVATE_TEST_LABEL',
            'PRIVATE_TEST_INPUT',
            'PRIVATE_TEST_EXPECTED',
            'PRIVATE_TEST_ACTUAL',
            'PRIVATE_TEST_STDERR',
            'PRIVATE_TEST_COMPILE_ERROR',
            'PRIVATE_TEST_RUNTIME_ERROR',
        ):
            self.assertNotIn(secret, raw_response)
        judge_report = response.get_json()['judge_report']
        self.assertEqual(judge_report['results'], [])
        self.assertEqual(judge_report['tests_passed'], 0)
        self.assertEqual(judge_report['tests_total'], 1)

    def test_task_submission_hides_runner_error_details(self):
        app = self.create_app()
        task_id = self._create_code_task(app)
        self.create_student(app)
        from app.api.student import CodeJudgeUnavailableError

        with app.test_client() as client, patch(
            'app.api.student.judge_task_submission',
            side_effect=CodeJudgeUnavailableError('PRIVATE_RUNNER_ERROR'),
        ):
            self.login(client)
            response = client.post(
                f'/api/tasks/{task_id}/submit', json={'answer': 'print(input())'}
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn('PRIVATE_RUNNER_ERROR', response.get_data(as_text=True))


# =====================================================================================
# C-03: password-change re-auth + session bump
# =====================================================================================


class PasswordChangeReauthTests(P0FixesBase):
    def test_password_change_requires_current_password(self):
        app = self.create_app()
        self.create_student(app)

        with app.test_client() as client:
            self.login(client)
            response = client.patch(
                '/api/users/me',
                json={'password': 'BrandNewStrongPass123!'},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn('текущий', response.get_json()['message'].lower())

    def test_password_change_rejects_wrong_current_password(self):
        app = self.create_app()
        self.create_student(app)

        with app.test_client() as client:
            self.login(client)
            response = client.patch(
                '/api/users/me',
                json={
                    'current_password': 'WrongOldPass123!',
                    'password': 'BrandNewStrongPass123!',
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_password_change_invalidates_existing_access_cookie(self):
        """After successful password change, the access-cookie issued before change is rejected."""
        app = self.create_app()
        self.create_student(app)

        with app.test_client() as client:
            self.login(client)
            initial = client.get('/api/auth/me')
            self.assertEqual(initial.status_code, 200)

            change = client.patch(
                '/api/users/me',
                json={
                    'current_password': 'StrongPass123!',
                    'password': 'BrandNewStrongPass123!',
                },
            )
            self.assertEqual(change.status_code, 200)

            after = client.get('/api/auth/me')
            self.assertEqual(after.status_code, 401)
            self.assertEqual(after.get_json().get('code'), 'session_revoked')

    def test_password_change_rejects_same_password(self):
        app = self.create_app()
        self.create_student(app)

        with app.test_client() as client:
            self.login(client)
            response = client.patch(
                '/api/users/me',
                json={
                    'current_password': 'StrongPass123!',
                    'password': 'StrongPass123!',
                },
            )

        self.assertEqual(response.status_code, 400)


# =====================================================================================
# S-06: admin self-block / self-delete protection
# =====================================================================================


class AdminSelfBlockTests(P0FixesBase):
    def test_admin_cannot_block_self(self):
        app = self.create_app()
        from app.models.user import UserRole

        admin_id = self.create_user(app, role=UserRole.ADMIN, email='admin@example.com')

        with app.test_client() as client:
            self.login(client, email='admin@example.com')
            response = client.patch(f'/api/admin/users/{admin_id}/block')

        self.assertEqual(response.status_code, 400)

    def test_superadmin_cannot_delete_self(self):
        app = self.create_app()
        from app.models.user import UserRole

        super_id = self.create_user(app, role=UserRole.SUPERADMIN, email='super@example.com')

        with app.test_client() as client:
            self.login(client, email='super@example.com')
            response = client.delete(f'/api/admin/users/{super_id}')

        self.assertEqual(response.status_code, 400)


# =====================================================================================
# C-06: class-join brute-force throttle
# =====================================================================================


class ClassJoinThrottleTests(P0FixesBase):
    def test_repeated_invalid_codes_eventually_throttle(self):
        app = self.create_app(
            CLASS_JOIN_RATE_LIMIT_WINDOW_SECONDS='600',
            CLASS_JOIN_RATE_LIMIT_MAX_FAILURES='3',
            CLASS_JOIN_RATE_LIMIT_BLOCK_SECONDS='600',
        )
        self.create_student(app)

        statuses: list[int] = []
        with app.test_client() as client:
            self.login(client)
            for _ in range(6):
                statuses.append(client.post('/api/classes/join', json={'code': 'NOSUCH-CODE'}).status_code)

        self.assertIn(429, statuses, f'expected 429 in statuses, got {statuses}')


# =====================================================================================
# C-07: media-route extension whitelist
# =====================================================================================


class MediaWhitelistTests(P0FixesBase):
    def test_mascot_route_rejects_html_extension(self):
        app = self.create_app()
        with app.test_client() as client:
            response = client.get('/api/mascot/payload.html')

        self.assertEqual(response.status_code, 404)

    def test_avatars_route_rejects_svg_extension(self):
        """SVG is excluded from the whitelist — it can carry inline scripts."""
        app = self.create_app()
        with app.test_client() as client:
            response = client.get('/api/media/avatars/exploit.svg')

        self.assertEqual(response.status_code, 404)

    def test_avatars_route_rejects_no_extension(self):
        app = self.create_app()
        with app.test_client() as client:
            response = client.get('/api/media/avatars/no-extension')

        self.assertEqual(response.status_code, 404)


# =====================================================================================
# S-11: PostgreSQL placeholder rejection in production
# =====================================================================================


class PostgresPasswordPlaceholderRejectionTests(P0FixesBase):
    def test_production_rejects_postgres_password_with_dev_fragment(self):
        with self.assertRaisesRegex(RuntimeError, 'PostgreSQL password'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                DATABASE_URL='postgresql+psycopg://codequest:DevPostgresLocalPassphrase000000001@db:5432/codequest',
                **_PROD_REDIS_ENV,
            )


if __name__ == '__main__':
    unittest.main()
