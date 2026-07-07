from __future__ import annotations

import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class BugHunterApiTests(unittest.TestCase):
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

    def create_app(self) -> object:
        tempdir = tempfile.TemporaryDirectory()
        self._tempdirs.append(tempdir)
        database_path = Path(tempdir.name) / 'test.db'
        media_dir = Path(tempdir.name) / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        env = {
            'APP_ENV': 'development',
            'SECRET_KEY': 'UnitTestSecretKey123!UnitTestSecretKey123!',
            'DATABASE_URL': f'sqlite:///{database_path.as_posix()}',
            'MEDIA_DIR': str(media_dir.resolve()),
            'CLIENT_URL': 'http://localhost:3000',
            'ENABLE_DEMO_DATA': 'false',
            'SUPERADMIN_BOOTSTRAP': 'false',
            'SESSION_COOKIE_SECURE': 'false',
            'GIGACHAT_VERIFY_SSL': 'true',
            'METRICS_DEBUG': 'false',
            'BUG_HUNTER_APPROVED_XP': '33',
        }

        with patch.dict(os.environ, env, clear=False):
            import app.core.config as config_module
            import app as app_module

            importlib.reload(config_module)
            importlib.reload(app_module)

            app = app_module.create_app()
            app.config.update(TESTING=True, BUG_HUNTER_APPROVED_XP=33)
            with app.app_context():
                from app.core.migrations import upgrade_database

                upgrade_database()
            self._apps.append(app)
            return app

    def create_user(self, app, *, email: str, password: str, role: str) -> None:
        from app.core.db import db
        from app.core.security import hash_password
        from app.models.user import User, UserRole

        with app.app_context():
            ag = None
            if role == 'student':
                ag = 'middle'
            elif role in ('teacher', 'parent', 'admin', 'superadmin'):
                ag = 'adult'
            db.session.add(
                User(
                    full_name=email.split('@')[0],
                    email=email,
                    password_hash=hash_password(password),
                    role=UserRole(role),
                    age_group=ag,
                )
            )
            db.session.commit()

    def login(self, client, login: str, password: str) -> None:
        response = client.post('/api/auth/login', json={'login': login, 'password': password})
        self.assertEqual(response.status_code, 200)

    def test_submit_and_approve_awards_xp(self):
        app = self.create_app()
        self.create_user(app, email='hunter@example.com', password='StudentPass123!', role='student')
        self.create_user(app, email='mods@example.com', password='AdminPass123!', role='admin')

        with app.test_client() as client:
            self.login(client, 'hunter@example.com', 'StudentPass123!')
            me0 = client.get('/api/auth/me').get_json() or {}
            xp0 = int((me0.get('user') or {}).get('xp') or 0)

            submit = client.post(
                '/api/support/bug-reports',
                data={
                    'description': 'Кнопка не реагирует на клик',
                    'reproduction_steps': 'Открыть урок, нажать «Отправить» два раза подряд',
                    'user_journey_path': 'Главная → Уроки → Урок Python → задача',
                },
            )
            self.assertEqual(submit.status_code, 201)
            body = submit.get_json() or {}
            self.assertIn('report', body)
            self.assertEqual(body.get('xp_on_approval_preview'), 33)
            rid = int(body['report']['id'])

            mine = client.get('/api/support/bug-reports/me')
            self.assertEqual(mine.status_code, 200)
            mj = mine.get_json() or {}
            self.assertEqual(len(mj.get('reports') or []), 1)

        with app.test_client() as client:
            self.login(client, 'mods@example.com', 'AdminPass123!')
            staff_before = client.get('/api/support/staff/bug-reports?status=pending')
            self.assertEqual(staff_before.status_code, 200)
            self.assertGreaterEqual(len((staff_before.get_json() or {}).get('reports') or []), 1)

            mod = client.patch(
                f'/api/support/staff/bug-reports/{rid}',
                json={'moderation_status': 'approved', 'moderator_note': 'Принято'},
            )
            self.assertEqual(mod.status_code, 200)
            self.assertEqual((mod.get_json() or {}).get('report', {}).get('moderation_status'), 'approved')

        with app.test_client() as client:
            self.login(client, 'hunter@example.com', 'StudentPass123!')
            me1 = client.get('/api/auth/me').get_json() or {}
            xp1 = int((me1.get('user') or {}).get('xp') or 0)
            self.assertEqual(xp1, xp0 + 33)

    def test_duplicate_approval_rejected(self):
        app = self.create_app()
        self.create_user(app, email='a@example.com', password='StudentPass123!', role='student')
        self.create_user(app, email='b@example.com', password='AdminPass123!', role='admin')

        with app.test_client() as client:
            self.login(client, 'a@example.com', 'StudentPass123!')
            submit = client.post(
                '/api/support/bug-reports',
                data={
                    'description': 'Падение вкладки',
                    'reproduction_steps': 'Воспроизвести любым способом',
                    'user_journey_path': '/profile',
                },
            )
            rid = int(submit.get_json()['report']['id'])

        with app.test_client() as client:
            self.login(client, 'b@example.com', 'AdminPass123!')
            r1 = client.patch(
                f'/api/support/staff/bug-reports/{rid}', json={'moderation_status': 'approved'}
            )
            self.assertEqual(r1.status_code, 200)
            r2 = client.patch(
                f'/api/support/staff/bug-reports/{rid}', json={'moderation_status': 'approved'}
            )
            self.assertEqual(r2.status_code, 409)

    def test_staff_bug_hunter_xp_setting_overrides_env(self):
        app = self.create_app()
        self.create_user(app, email='stu2@example.com', password='StudentPass123!', role='student')
        self.create_user(app, email='adm2@example.com', password='AdminPass123!', role='admin')

        with app.test_client() as client:
            self.login(client, 'adm2@example.com', 'AdminPass123!')
            got = client.get('/api/support/staff/bug-hunter/settings')
            self.assertEqual(got.status_code, 200)
            self.assertEqual((got.get_json() or {}).get('approved_xp'), 33)

            ch = client.patch('/api/support/staff/bug-hunter/settings', json={'approved_xp': 91})
            self.assertEqual(ch.status_code, 200)

        with app.test_client() as client:
            self.login(client, 'stu2@example.com', 'StudentPass123!')
            me0 = client.get('/api/auth/me').get_json() or {}
            xp0 = int((me0.get('user') or {}).get('xp') or 0)
            submit = client.post(
                '/api/support/bug-reports',
                data={
                    'description': 'Неверный цвет кнопки',
                    'reproduction_steps': 'Открыть форму отправки задачи для проверки',
                    'user_journey_path': '/roadmap → урок → задание',
                },
            )
            self.assertEqual(submit.status_code, 201)
            self.assertEqual((submit.get_json() or {}).get('xp_on_approval_preview'), 91)
            rid = int(submit.get_json()['report']['id'])

        with app.test_client() as client:
            self.login(client, 'adm2@example.com', 'AdminPass123!')
            mod = client.patch(
                f'/api/support/staff/bug-reports/{rid}', json={'moderation_status': 'approved'}
            )
            self.assertEqual(mod.status_code, 200)

        with app.test_client() as client:
            self.login(client, 'stu2@example.com', 'StudentPass123!')
            me1 = client.get('/api/auth/me').get_json() or {}
            xp1 = int((me1.get('user') or {}).get('xp') or 0)
            self.assertEqual(xp1, xp0 + 91)

    def test_screenshot_optional_multipart_accepted(self):
        app = self.create_app()
        self.create_user(app, email='snap@example.com', password='StudentPass123!', role='student')

        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow not installed')

        buf = io.BytesIO()
        Image.new('RGB', (40, 20), color='red').save(buf, format='PNG')
        png_bytes = buf.getvalue()

        with app.test_client() as client:
            self.login(client, 'snap@example.com', 'StudentPass123!')
            submit = client.post(
                '/api/support/bug-reports',
                data={
                    'description': 'Сломался предпросмотр',
                    'reproduction_steps': 'Загрузить файл как в этом репорте',
                    'user_journey_path': '/dashboard',
                    'screenshot': (io.BytesIO(png_bytes), 'scr.png'),
                },
                content_type='multipart/form-data',
            )
            self.assertEqual(submit.status_code, 201)
            shot = (submit.get_json() or {}).get('report', {}).get('screenshot')
            self.assertIsNotNone(shot)
            self.assertTrue(str(shot.get('url') or '').startswith('/api/media/'))
