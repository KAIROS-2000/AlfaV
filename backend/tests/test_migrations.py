from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class MigrationDisciplineTests(unittest.TestCase):
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

    def create_app(self):
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
            'GIGACHAT_VERIFY_SSL': 'true',
            'METRICS_DEBUG': 'false',
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

        with patch.dict(os.environ, env, clear=True):
            import app.core.config as config_module
            import app as app_module

            importlib.reload(config_module)
            importlib.reload(app_module)
            app = app_module.create_app()
            app.config.update(TESTING=True)
            self._apps.append(app)
            return app

    def test_upgrade_database_records_ordered_schema_migrations(self):
        app = self.create_app()

        with app.app_context():
            from app.core.db import db
            from app.core.migrations import upgrade_database

            applied = upgrade_database()
            second_run = upgrade_database()
            inspector = inspect(db.engine)
            columns = {column['name'] for column in inspector.get_columns('user_progress')}
            user_columns = {column['name'] for column in inspector.get_columns('users')}
            lesson_columns = {
                column['name']: column for column in inspector.get_columns('lessons')
            }
            lesson_foreign_keys = inspector.get_foreign_keys('lessons')
            lesson_indexes = inspector.get_indexes('lessons')
            notification_tables = {
                'user_notifications',
                'user_notification_preferences',
                'email_notification_logs',
            }
            revisions = [
                row[0]
                for row in db.session.execute(text('SELECT revision FROM schema_migrations ORDER BY revision')).all()
            ]

        self.assertIn('0001_current_schema_baseline', applied)
        self.assertEqual(second_run, [])
        self.assertIn('schema_migrations', inspector.get_table_names())
        self.assertIn('started_at', columns)
        self.assertIn('teacher_approval_status', user_columns)
        self.assertIn('teacher_rejection_expires_at', user_columns)
        self.assertTrue(notification_tables.issubset(set(inspector.get_table_names())))
        self.assertIn('0003_session_and_progress_columns', revisions)
        self.assertIn('0007_teacher_approval_status', revisions)
        self.assertIn('0008_teacher_rejection_expiration', revisions)
        self.assertIn('0021_user_notifications', revisions)
        self.assertIn('0023_manager_role_enum_compatibility', revisions)
        self.assertIn('0025_lesson_authoring_schema_constraints', revisions)
        self.assertIn('0026_user_legal_acceptance', revisions)
        self.assertIn('legal_documents_version', user_columns)
        self.assertIn('legal_documents_accepted_at', user_columns)
        self.assertFalse(lesson_columns['updated_at']['nullable'])
        self.assertTrue(
            any(
                foreign_key.get('constrained_columns') == ['created_by_id']
                and foreign_key.get('referred_table') == 'users'
                and foreign_key.get('referred_columns') == ['id']
                and str((foreign_key.get('options') or {}).get('ondelete') or '').upper() == 'SET NULL'
                for foreign_key in lesson_foreign_keys
            )
        )
        self.assertTrue(
            any(index.get('column_names') == ['created_by_id'] for index in lesson_indexes)
        )

    def test_postgresql_corrective_migration_emits_orm_constraints(self):
        with patch.dict(os.environ, {'CODEQUEST_SKIP_DOTENV': 'true'}, clear=True):
            migration = importlib.import_module(
                'app.migrations.0025_lesson_authoring_schema_constraints'
            )
        timestamp_without_timezone = SimpleNamespace(timezone=False)
        inspector = MagicMock()
        inspector.get_table_names.return_value = ['lessons', 'users']
        inspector.get_columns.return_value = [
            {'name': 'created_by_id', 'nullable': True},
            {'name': 'updated_at', 'nullable': True, 'type': timestamp_without_timezone},
            {'name': 'published_at', 'nullable': True, 'type': timestamp_without_timezone},
            {'name': 'archived_at', 'nullable': True, 'type': timestamp_without_timezone},
        ]
        inspector.get_foreign_keys.return_value = []
        inspector.get_indexes.return_value = []

        connection = MagicMock()
        engine = MagicMock()
        engine.dialect.name = 'postgresql'
        engine.dialect.identifier_preparer.quote.side_effect = lambda identifier: f'"{identifier}"'
        engine.begin.return_value.__enter__.return_value = connection
        fake_db = SimpleNamespace(engine=engine)

        with patch.object(migration, 'inspect', return_value=inspector):
            migration.upgrade(fake_db)

        statements = [str(call.args[0]) for call in connection.execute.call_args_list]
        combined = '\n'.join(statements)
        self.assertIn('ALTER COLUMN updated_at SET NOT NULL', combined)
        self.assertIn('TIMESTAMP WITH TIME ZONE', combined)
        self.assertIn('FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL', combined)
        self.assertIn('CREATE INDEX ix_lessons_created_by_id', combined)

    def test_postgresql_runner_holds_and_releases_session_advisory_lock(self):
        from app.core import migrations as migration_runner

        connection = MagicMock()
        connection.in_transaction.return_value = False
        engine = MagicMock()
        engine.dialect.name = 'postgresql'
        engine.connect.return_value = connection

        with self.assertRaisesRegex(RuntimeError, 'deploy failed'):
            with migration_runner._locked_migration_connection(engine) as locked_connection:
                self.assertIs(locked_connection, connection)
                raise RuntimeError('deploy failed')

        statements = [str(call.args[0]) for call in connection.execute.call_args_list]
        self.assertEqual(statements[0], 'SELECT pg_advisory_lock(:lock_id)')
        self.assertEqual(statements[-1], 'SELECT pg_advisory_unlock(:lock_id)')
        self.assertEqual(
            connection.execute.call_args_list[0].args[1]['lock_id'],
            migration_runner.POSTGRES_MIGRATION_ADVISORY_LOCK_ID,
        )
        self.assertEqual(connection.commit.call_count, 2)
        connection.close.assert_called_once_with()

    def test_connection_aware_migration_and_revision_share_transaction(self):
        from app.core import migrations as migration_runner

        transaction_active = {'value': False}
        transaction = MagicMock()

        def enter_transaction():
            transaction_active['value'] = True
            return transaction

        def exit_transaction(*_args):
            transaction_active['value'] = False
            return False

        transaction.__enter__.side_effect = enter_transaction
        transaction.__exit__.side_effect = exit_transaction
        connection = MagicMock()
        connection.begin.return_value = transaction

        upgrade_calls = []

        def upgrade(_db, *, connection=None):
            self.assertTrue(transaction_active['value'])
            upgrade_calls.append(connection)

        def execute(statement, *_args, **_kwargs):
            if 'INSERT INTO schema_migrations' in str(statement):
                self.assertTrue(transaction_active['value'])

        connection.execute.side_effect = execute
        module = SimpleNamespace(upgrade=upgrade)
        migration = migration_runner.Migration('9998_atomic', 'atomic test', 'tests.atomic')

        with patch.object(migration_runner.importlib, 'import_module', return_value=module):
            migration_runner._apply_migration(connection, migration)

        self.assertEqual(upgrade_calls, [connection])
        self.assertTrue(any(
            'INSERT INTO schema_migrations' in str(call.args[0])
            for call in connection.execute.call_args_list
        ))
        transaction.__exit__.assert_called_once()

    def test_failed_connection_aware_migration_does_not_record_revision(self):
        from app.core import migrations as migration_runner

        connection = MagicMock()

        def upgrade(_db, *, connection=None):  # noqa: ARG001
            raise RuntimeError('migration failed')

        module = SimpleNamespace(upgrade=upgrade)
        migration = migration_runner.Migration('9999_failed', 'failure test', 'tests.failed')

        with patch.object(migration_runner.importlib, 'import_module', return_value=module):
            with self.assertRaisesRegex(RuntimeError, 'migration failed'):
                migration_runner._apply_migration(connection, migration)

        self.assertFalse(any(
            'INSERT INTO schema_migrations' in str(call.args[0])
            for call in connection.execute.call_args_list
        ))

    def test_provision_first_superadmin_uses_password_file_and_writes_audit_log(self):
        app = self.create_app()
        password = 'ProvisionedAdminPass123!'
        password_file = Path(self._tempdirs[-1].name) / 'provisioning-password'
        password_file.write_text(password + '\n', encoding='utf-8')
        command_env = {
            'PROVISION_SUPERADMIN_EMAIL': 'first-admin@example.com',
            'PROVISION_SUPERADMIN_NAME': 'First Administrator',
            'PROVISION_SUPERADMIN_PASSWORD_FILE': str(password_file),
        }

        result = app.test_cli_runner().invoke(
            args=['provision-first-superadmin'],
            env=command_env,
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn('provisioned successfully', result.output)
        self.assertNotIn(password, result.output)
        self.assertNotIn(str(password_file), result.output)
        with app.app_context():
            from app.core.security import verify_password
            from app.models.user import AdminAuditLog, User, UserRole

            user = User.query.one()
            self.assertEqual(user.email, 'first-admin@example.com')
            self.assertEqual(user.role, UserRole.SUPERADMIN)
            self.assertTrue(user.is_active)
            self.assertTrue(user.email_verified)
            self.assertTrue(verify_password(password, user.password_hash))
            audit = AdminAuditLog.query.filter_by(
                action='initial_superadmin_provisioned'
            ).one()
            self.assertEqual(audit.actor_user_id, user.id)
            self.assertEqual(audit.entity_id, user.id)
            self.assertEqual(audit.details_json['credential_source'], 'password_file')
            self.assertNotIn(password, str(audit.details_json))
            self.assertNotIn(str(password_file), str(audit.details_json))

    def test_provision_first_superadmin_refuses_when_one_already_exists(self):
        app = self.create_app()
        password = 'ProvisionedAdminPass123!'
        password_file = Path(self._tempdirs[-1].name) / 'provisioning-password'
        password_file.write_text(password, encoding='utf-8')
        command_env = {
            'PROVISION_SUPERADMIN_EMAIL': 'first-admin@example.com',
            'PROVISION_SUPERADMIN_NAME': 'First Administrator',
            'PROVISION_SUPERADMIN_PASSWORD_FILE': str(password_file),
        }
        runner = app.test_cli_runner()
        first = runner.invoke(args=['provision-first-superadmin'], env=command_env)
        command_env['PROVISION_SUPERADMIN_EMAIL'] = 'second-admin@example.com'
        second = runner.invoke(args=['provision-first-superadmin'], env=command_env)

        self.assertEqual(first.exit_code, 0, first.output)
        self.assertNotEqual(second.exit_code, 0)
        self.assertIn('superadmin already exists', second.output)
        self.assertNotIn(password, second.output)
        with app.app_context():
            from app.models.user import AdminAuditLog, User, UserRole

            self.assertEqual(User.query.filter_by(role=UserRole.SUPERADMIN).count(), 1)
            self.assertEqual(
                AdminAuditLog.query.filter_by(action='initial_superadmin_provisioned').count(),
                1,
            )

    def test_provision_first_superadmin_does_not_accept_plaintext_env_password(self):
        app = self.create_app()
        password = 'ProvisionedAdminPass123!'
        result = app.test_cli_runner().invoke(
            args=['provision-first-superadmin'],
            env={
                'PROVISION_SUPERADMIN_EMAIL': 'first-admin@example.com',
                'PROVISION_SUPERADMIN_NAME': 'First Administrator',
                'PROVISION_SUPERADMIN_PASSWORD_FILE': '',
                'PROVISION_SUPERADMIN_PASSWORD': password,
            },
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn('PROVISION_SUPERADMIN_PASSWORD_FILE', result.output)
        self.assertNotIn(password, result.output)


if __name__ == '__main__':
    unittest.main()
