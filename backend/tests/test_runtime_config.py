from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import request

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_PROD_REDIS_ENV = {
    'REDIS_URL': 'redis://127.0.0.1:6379/0',
    'REDIS_PASSWORD': 'UnitTestRedisPassword0123456789ABC!',
}
_PROD_EMAIL_ENV = {
    'SEND_MAIL': 'true',
    'EMAIL_DRY_RUN': 'false',
    'EMAIL_PROVIDER': 'unisender_go',
    'UNISENDER_GO_API_KEY': 'unit-production-api-key-73409852',
    'UNISENDER_GO_API_URL': 'https://mail-api.example.test/v1',
    'EMAIL_FROM': 'no-reply@example.test',
    'EMAIL_REPLY_TO': 'support@example.test',
    'FRONTEND_PUBLIC_URL': 'https://frontend.example',
}


class RuntimeConfigValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdirs: list[tempfile.TemporaryDirectory[str]] = []
        self._apps = []

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
            'CODEQUEST_SKIP_DOTENV': 'true',
            'APP_ENV': 'development',
            'SECRET_KEY': 'UnitTestSecretKey123!UnitTestSecretKey123!',
            'DATABASE_URL': f'sqlite:///{database_path.as_posix()}',
            'CLIENT_URL': 'http://localhost:3000',
            'LEGAL_DOCUMENTS_VERSION': 'test-legal-v1',
            'ENABLE_DEMO_DATA': 'false',
            'SUPERADMIN_BOOTSTRAP': 'false',
            'SESSION_COOKIE_SECURE': 'false',
            'SESSION_COOKIE_SAMESITE': 'Strict',
            'GIGACHAT_VERIFY_SSL': 'true',
            'CODE_JUDGE_RUNNER_URL': '',
            'CODE_JUDGE_RUNNER_TOKEN': '',
            'METRICS_DEBUG': 'false',
            'TRUST_PROXY': 'false',
            'SEND_MAIL': 'false',
            'REDIS_URL': '',
            'REDIS_PASSWORD': '',
            'REDIS_PASSWORD_FILE': '',
            'POSTGRES_PASSWORD_FILE': '',
            'CODE_JUDGE_RUNNER_TOKEN_FILE': '',
            'READINESS_REQUIRE_REDIS': 'false',
            'READINESS_REQUIRE_JUDGE': 'false',
            'ENABLE_AUDIT_LOG_DAILY_EXPORT_THREAD': 'false',
            'ENABLE_PARENT_WEEKLY_PROGRESS_EMAIL_THREAD': 'false',
        }
        env.update(env_overrides)

        with patch.dict(os.environ, env, clear=True):
            import app.core.config as config_module
            import app as app_module

            importlib.reload(config_module)
            importlib.reload(app_module)

            app = app_module.create_app()
            app.config.update(TESTING=True)
            self._apps.append(app)
            return app

    def test_production_rejects_short_secret_key(self):
        with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='wemogw!325gzz',
                **_PROD_REDIS_ENV,
            )

    def test_production_accepts_strong_hex_secret_key(self):
        app = self.create_app(
            APP_ENV='production',
            SESSION_COOKIE_SECURE='true',
            CLIENT_URL='https://frontend.example',
            SECRET_KEY='a1' * 32,
            GIGACHAT_VERIFY_SSL='true',
            **_PROD_REDIS_ENV,
        )
        self.assertTrue(app.config['IS_PRODUCTION'])

    def test_production_requires_legal_documents_version(self):
        with self.assertRaisesRegex(RuntimeError, 'LEGAL_DOCUMENTS_VERSION'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                LEGAL_DOCUMENTS_VERSION='',
                **_PROD_REDIS_ENV,
            )

    def test_production_rejects_placeholder_legal_documents_version(self):
        with self.assertRaisesRegex(RuntimeError, 'LEGAL_DOCUMENTS_VERSION'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                LEGAL_DOCUMENTS_VERSION='development-v1',
                **_PROD_REDIS_ENV,
            )

    def test_production_accepts_complete_email_configuration(self):
        app = self.create_app(
            APP_ENV='production',
            SESSION_COOKIE_SECURE='true',
            CLIENT_URL='https://frontend.example',
            SECRET_KEY='a1' * 32,
            **_PROD_REDIS_ENV,
            **_PROD_EMAIL_ENV,
        )
        self.assertTrue(app.config['SEND_MAIL'])

    def test_production_send_mail_requires_api_key(self):
        email_env = {**_PROD_EMAIL_ENV, 'UNISENDER_GO_API_KEY': ''}
        with self.assertRaisesRegex(RuntimeError, 'UNISENDER_GO_API_KEY'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                **_PROD_REDIS_ENV,
                **email_env,
            )

    def test_production_send_mail_rejects_insecure_frontend_url(self):
        email_env = {**_PROD_EMAIL_ENV, 'FRONTEND_PUBLIC_URL': 'http://frontend.example'}
        with self.assertRaisesRegex(RuntimeError, 'FRONTEND_PUBLIC_URL'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                **_PROD_REDIS_ENV,
                **email_env,
            )

    def test_production_rejects_client_url_that_is_not_an_exact_https_origin(self):
        invalid_origins = (
            'http://frontend.example',
            'https://frontend.example/app',
            'https://frontend.example/',
            'https://frontend.example?tenant=one',
            'https://frontend.example#section',
            'https://user:password@frontend.example',
            'https://frontend.example,https://other.example',
        )
        for client_url in invalid_origins:
            with self.subTest(client_url=client_url):
                with self.assertRaisesRegex(RuntimeError, 'CLIENT_URL'):
                    self.create_app(
                        APP_ENV='production',
                        SESSION_COOKIE_SECURE='true',
                        CLIENT_URL=client_url,
                        SECRET_KEY='a1' * 32,
                        **_PROD_REDIS_ENV,
                    )

    def test_production_send_mail_rejects_frontend_url_with_path(self):
        email_env = {
            **_PROD_EMAIL_ENV,
            'FRONTEND_PUBLIC_URL': 'https://frontend.example/account/setup',
        }
        with self.assertRaisesRegex(RuntimeError, 'FRONTEND_PUBLIC_URL'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                **_PROD_REDIS_ENV,
                **email_env,
            )

    def test_production_send_mail_rejects_dry_run(self):
        email_env = {**_PROD_EMAIL_ENV, 'EMAIL_DRY_RUN': 'true'}
        with self.assertRaisesRegex(RuntimeError, 'EMAIL_DRY_RUN'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                **_PROD_REDIS_ENV,
                **email_env,
            )

    def test_production_rejects_lax_session_cookie_samesite(self):
        with self.assertRaisesRegex(RuntimeError, 'SESSION_COOKIE_SAMESITE'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                SESSION_COOKIE_SAMESITE='Lax',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                **_PROD_REDIS_ENV,
            )

    def test_production_rejects_jwt_keyring_without_current_key(self):
        with self.assertRaisesRegex(RuntimeError, 'JWT_SIGNING_KEY_ID'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                JWT_SIGNING_KEY_ID='current',
                JWT_SIGNING_KEYS='previous=' + ('b2' * 32),
                GIGACHAT_VERIFY_SSL='true',
                **_PROD_REDIS_ENV,
            )

    def test_production_accepts_jwt_keyring_rotation(self):
        app = self.create_app(
            APP_ENV='production',
            SESSION_COOKIE_SECURE='true',
            CLIENT_URL='https://frontend.example',
            SECRET_KEY='a1' * 32,
            JWT_SIGNING_KEY_ID='current',
            JWT_SIGNING_KEYS='current=' + ('c3' * 32) + ',previous=' + ('d4' * 32),
            GIGACHAT_VERIFY_SSL='true',
            **_PROD_REDIS_ENV,
        )
        self.assertTrue(app.config['IS_PRODUCTION'])

    def test_production_rejects_placeholder_secret_key(self):
        with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='totally-random-change-me-key-material-1234567890',
                **_PROD_REDIS_ENV,
            )

    def test_production_rejects_long_but_low_entropy_secret_key(self):
        """A 35-char key of only lowercase letters must fail the entropy heuristic."""
        with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='abcdefghijklmnopqrstuvwxyzabcdefghi',
                **_PROD_REDIS_ENV,
            )

    def test_production_rejects_same_char_secret_key(self):
        with self.assertRaisesRegex(RuntimeError, 'SECRET_KEY'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a' * 64,
                **_PROD_REDIS_ENV,
            )

    def test_development_allows_weak_secret_key_for_local_ergonomics(self):
        app = self.create_app(
            APP_ENV='development',
            SECRET_KEY='short-and-weak',
        )
        self.assertFalse(app.config['IS_PRODUCTION'])

    def test_request_body_limit_rejects_oversized_payload_with_json(self):
        app = self.create_app(MAX_CONTENT_LENGTH_BYTES='128')

        @app.post('/api/health/body-limit-test')
        def body_limit_test():
            return {'size': len(request.get_data())}

        with app.test_client() as client:
            response = client.post(
                '/api/health/body-limit-test',
                data=b'x' * 129,
                content_type='application/octet-stream',
                headers={'Origin': 'http://localhost:3000'},
            )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            response.get_json(),
            {
                'message': 'Request body exceeds the configured size limit.',
                'code': 'request_too_large',
                'max_bytes': 128,
            },
        )

    def test_request_body_limit_configuration_is_validated(self):
        with self.assertRaisesRegex(RuntimeError, 'MAX_CONTENT_LENGTH_BYTES'):
            self.create_app(MAX_CONTENT_LENGTH_BYTES='0')

    def test_liveness_and_readiness_are_distinct(self):
        app = self.create_app()
        with app.test_client() as client:
            liveness_response = client.get('/api/live')
            readiness_response = client.get('/api/ready')
            legacy_response = client.get('/api/health')

        self.assertEqual(liveness_response.status_code, 200)
        self.assertEqual(liveness_response.get_json(), {'status': 'ok'})
        self.assertEqual(readiness_response.status_code, 200)
        self.assertEqual(
            readiness_response.get_json()['checks'],
            {'database': True, 'redis': None, 'judge': None},
        )
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(legacy_response.get_json()['status'], 'ok')

    def test_readiness_returns_503_when_database_check_fails(self):
        app = self.create_app()
        import app as app_module

        with patch.object(app_module, '_database_ready', return_value=False):
            with app.test_client() as client:
                liveness_response = client.get('/api/live')
                readiness_response = client.get('/api/ready')
                legacy_response = client.get('/api/health')

        self.assertEqual(liveness_response.status_code, 200)
        self.assertEqual(readiness_response.status_code, 503)
        self.assertFalse(readiness_response.get_json()['checks']['database'])
        self.assertEqual(legacy_response.status_code, 503)

    def test_readiness_returns_503_when_required_redis_is_missing(self):
        app = self.create_app(READINESS_REQUIRE_REDIS='true', REDIS_URL='')
        with app.test_client() as client:
            response = client.get('/api/ready')

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()['checks']['redis'])

    def test_readiness_returns_503_when_configured_redis_ping_fails(self):
        app = self.create_app(
            READINESS_REQUIRE_REDIS='true',
            REDIS_URL='redis://127.0.0.1:6379/0',
        )
        with patch('app.core.redis_client.redis_ping_with_timeout_ms', return_value=False):
            with app.test_client() as client:
                response = client.get('/api/ready')

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()['checks']['redis'])

    def test_readiness_returns_503_when_required_judge_is_missing(self):
        app = self.create_app(
            READINESS_REQUIRE_JUDGE='true',
            CODE_JUDGE_RUNNER_URL='',
        )
        with app.test_client() as client:
            response = client.get('/api/ready')

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()['checks']['judge'])

    def test_readiness_returns_503_when_judge_probe_fails(self):
        app = self.create_app(
            READINESS_REQUIRE_JUDGE='true',
            READINESS_JUDGE_TIMEOUT_MS='250',
            CODE_JUDGE_RUNNER_URL='http://judge-gateway:8081/execute',
        )
        import app as app_module

        with patch.object(app_module, '_probe_judge_health', return_value=False) as probe:
            with app.test_client() as client:
                response = client.get('/api/ready')

        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()['checks']['judge'])
        probe.assert_called_once_with('http://judge-gateway:8081/execute', 250)

    def test_judge_probe_uses_runner_origin_health_endpoint(self):
        self.create_app()
        import app as app_module

        class HealthyResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read():
                return b'{"status":"ok"}'

        with patch.object(
            app_module.urllib_request,
            'urlopen',
            return_value=HealthyResponse(),
        ) as urlopen:
            healthy = app_module._probe_judge_health(
                'http://judge-gateway:8081/execute?ignored=yes',
                250,
            )

        self.assertTrue(healthy)
        sent_request = urlopen.call_args.args[0]
        self.assertEqual(sent_request.full_url, 'http://judge-gateway:8081/health')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 0.25)

    def test_production_does_not_expose_disabled_gigachat_credentials(self):
        app = self.create_app(
            APP_ENV='production',
            SESSION_COOKIE_SECURE='true',
            CLIENT_URL='https://frontend.example',
            SECRET_KEY='Abcdef1234567890!Abcdef1234567890!Abcdef',
            GIGACHAT_AUTH_KEY='must-not-enter-app-config',
            GIGACHAT_VERIFY_SSL='false',
            **_PROD_REDIS_ENV,
        )
        self.assertNotIn('GIGACHAT_AUTH_KEY', app.config)
        self.assertNotIn('GIGACHAT_API_URL', app.config)

    def test_production_requires_redis_url(self):
        with self.assertRaisesRegex(RuntimeError, 'REDIS_URL'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                REDIS_URL='',
                REDIS_PASSWORD='UnitTestRedisPassword0123456789ABC!',
            )

    def test_production_requires_redis_password_strength(self):
        with self.assertRaisesRegex(RuntimeError, 'Redis password'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                REDIS_URL='redis://127.0.0.1:6379/0',
                REDIS_PASSWORD='short',
            )

    def test_production_rejects_placeholder_redis_url(self):
        with self.assertRaisesRegex(RuntimeError, 'REDIS_URL'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                REDIS_URL='redis://placeholder-host:6379/0',
                REDIS_PASSWORD='UnitTestRedisPassword0123456789ABC!',
            )

    def test_production_rejects_rediss_url(self):
        with self.assertRaisesRegex(RuntimeError, 'redis://'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                REDIS_URL='rediss://127.0.0.1:6379/0',
                REDIS_PASSWORD='UnitTestRedisPassword0123456789ABC!',
            )

    def test_production_rejects_placeholder_redis_password(self):
        with self.assertRaisesRegex(RuntimeError, 'Redis password'):
            self.create_app(
                APP_ENV='production',
                SESSION_COOKIE_SECURE='true',
                CLIENT_URL='https://frontend.example',
                SECRET_KEY='a1' * 32,
                GIGACHAT_VERIFY_SSL='true',
                REDIS_URL='redis://127.0.0.1:6379/0',
                REDIS_PASSWORD='prefix-change-me-suffix-123456789012',
            )

    def test_trust_proxy_applies_forwarded_for_and_proto(self):
        app = self.create_app(TRUST_PROXY='true')

        @app.get('/_test/request-meta')
        def request_meta():
            return {
                'remote_addr': request.remote_addr,
                'scheme': request.scheme,
            }

        with app.test_client() as client:
            response = client.get(
                '/_test/request-meta',
                headers={
                    'X-Forwarded-For': '203.0.113.10',
                    'X-Forwarded-Proto': 'https',
                    'X-Forwarded-Host': 'api.example.com',
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload['remote_addr'], '203.0.113.10')
            self.assertEqual(payload['scheme'], 'https')


if __name__ == '__main__':
    unittest.main()
