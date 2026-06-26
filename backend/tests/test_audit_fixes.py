"""Regression tests for the H1–H6 functional bugs found in the full-system audit.

H1 — parent consent (allow_learning_analytics_display) must gate EVERY analytics
     endpoint, not just /digest.
H2 — allow_achievement_sharing must actually gate the achievements endpoint.
H3 — a one-time child-link code cannot be redeemed by a second parent.
H4 — deleting a user who has support tickets / staff & parent-teacher threads /
     parent-child links must succeed (no FK IntegrityError) — verified with
     SQLite foreign-key enforcement ON.
H5 — staff cannot approve their OWN bug report and self-award XP.
H6 — a student cannot revert a teacher-graded ("checked") assignment by
     re-submitting.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class AuditFixesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._apps: list = []
        self._tempdirs: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self) -> None:
        for app in self._apps:
            with app.app_context():
                from app.core.db import db

                db.session.remove()
                db.engine.dispose()
        for tempdir in self._tempdirs:
            tempdir.cleanup()

    def create_app(self, *, enforce_fk: bool = False):
        tempdir = tempfile.TemporaryDirectory()
        self._tempdirs.append(tempdir)
        database_path = Path(tempdir.name) / 'audit.db'
        env = {
            'APP_ENV': 'development',
            'SECRET_KEY': 'UnitTestSecretKey123!UnitTestSecretKey123!',
            'DATABASE_URL': f'sqlite:///{database_path.as_posix()}',
            'CLIENT_URL': 'http://localhost:3000',
            'FRONTEND_PUBLIC_URL': 'http://localhost:3000',
            'SEND_MAIL': 'false',  # auto-verify registrations; no email
            'EMAIL_DRY_RUN': 'true',
            'ENABLE_DEMO_DATA': 'false',
            'SUPERADMIN_BOOTSTRAP': 'false',
            'STAFF_EMAIL_DOMAIN': '',
            'SESSION_COOKIE_SECURE': 'false',
            'GIGACHAT_VERIFY_SSL': 'true',
            'METRICS_DEBUG': 'false',
            'THROTTLE_BACKEND': 'db',
            'ENABLE_SITE_ACTIVITY_LOG': 'false',
        }
        with patch.dict(os.environ, env, clear=False):
            import app.core.config as config_module
            import app as app_module

            importlib.reload(config_module)
            importlib.reload(app_module)

            app = app_module.create_app()
            app.config.update(TESTING=True)
            with app.app_context():
                from app import models  # noqa: F401
                from app.core.db import db
                from app.core.runtime_schema import ensure_runtime_schema

                if enforce_fk:
                    from sqlalchemy import event

                    engine = db.engine
                    if not getattr(engine, '_fk_pragma', False):
                        @event.listens_for(engine, 'connect')
                        def _enable_fk(dbapi_conn, _rec):  # noqa: ANN001
                            cur = dbapi_conn.cursor()
                            cur.execute('PRAGMA foreign_keys=ON')
                            cur.close()

                        engine._fk_pragma = True
                    engine.dispose()  # re-open connections with the pragma listener

                db.create_all()
                ensure_runtime_schema()
            self._apps.append(app)
            return app

    # --- helpers ---------------------------------------------------------

    def make_user(self, app, *, email, role, password='StrongPass123!', full_name='Test User', age_group='middle'):
        from app.core.db import db
        from app.core.security import hash_password
        from app.models.user import TEACHER_APPROVAL_APPROVED, User, UserRole

        with app.app_context():
            user = User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole(role),
                age_group=age_group if role == 'student' else None,
                is_active=True,
                email_verified=True,
                email_verified_at=datetime.now(UTC),
                teacher_approval_status=TEACHER_APPROVAL_APPROVED,
                password_changed_at=datetime.now(UTC),
            )
            db.session.add(user)
            db.session.commit()
            return user.id

    def client_for(self, app, email, password='StrongPass123!'):
        client = app.test_client()
        resp = client.post('/api/auth/login', json={'login': email, 'password': password})
        assert resp.status_code == 200, (email, resp.status_code, resp.get_json())
        return client

    def register_student(self, app, email, phone):
        client = app.test_client()
        resp = client.post('/api/auth/register', json={
            'full_name': 'Kid', 'email': email, 'phone': phone,
            'password': 'StrongPass123!', 'role': 'student', 'age_group': 'middle',
        })
        assert resp.status_code == 201, ('student reg', resp.status_code, resp.get_json())
        return client, resp.get_json()['user']['id']

    def register_parent_and_link(self, app, student_client, parent_email):
        # student generates a code
        code_resp = student_client.post('/api/student/parent-link-code', json={})
        assert code_resp.status_code in (200, 201), code_resp.get_json()
        code = code_resp.get_json()['code']
        # parent registers (email only), fills profile, links
        parent_client = app.test_client()
        preg = parent_client.post('/api/auth/register', json={'email': parent_email, 'role': 'parent'})
        assert preg.status_code == 201, preg.get_json()
        parent_client.patch('/api/users/me', json={'full_name': 'Parent', 'phone': '+7 (912) 111-22-33'})
        link = parent_client.post('/api/parent/children/link', json={'code': code})
        assert link.status_code == 201, ('link', link.status_code, link.get_json())
        kids = parent_client.get('/api/parent/children').get_json()['children']
        return parent_client, kids[0]['id'], code

    # --- H1 ---------------------------------------------------------------

    def test_h1_analytics_consent_gates_every_endpoint(self):
        app = self.create_app()
        student_client, _ = self.register_student(app, 'kid1@example.com', '+7 (912) 000-00-11')
        parent_client, child_id, _ = self.register_parent_and_link(app, student_client, 'p1@example.com')

        # turn analytics display OFF
        r = parent_client.patch(f'/api/parent/children/{child_id}/consent',
                                json={'allow_learning_analytics_display': False})
        self.assertEqual(r.status_code, 200)

        # digest already gated (baseline)
        self.assertNotIn('learning_activity_minutes_estimate',
                         parent_client.get(f'/api/parent/children/{child_id}/digest').get_json())

        # every other analytics endpoint must now be gated too
        for path in ('summary', 'activity', 'skills', 'practice-history'):
            body = parent_client.get(f'/api/parent/children/{child_id}/{path}').get_json()
            self.assertTrue(body.get('analytics_disabled'), f'{path} not gated: {body}')
        # summary must not leak real numbers
        summary = parent_client.get(f'/api/parent/children/{child_id}/summary').get_json()
        self.assertEqual(summary['summary']['completed_lessons'], 0)
        # dashboard must not embed the summary
        dash = parent_client.get('/api/parent/dashboard').get_json()
        self.assertNotIn('summary', dash)
        self.assertTrue(dash.get('analytics_disabled'))

        # re-enable → data flows again
        parent_client.patch(f'/api/parent/children/{child_id}/consent',
                            json={'allow_learning_analytics_display': True})
        ok = parent_client.get(f'/api/parent/children/{child_id}/summary').get_json()
        self.assertNotIn('analytics_disabled', ok)

    # --- H2 ---------------------------------------------------------------

    def test_h2_achievement_sharing_gates_achievements(self):
        app = self.create_app()
        student_client, _ = self.register_student(app, 'kid2@example.com', '+7 (912) 000-00-12')
        parent_client, child_id, _ = self.register_parent_and_link(app, student_client, 'p2@example.com')

        parent_client.patch(f'/api/parent/children/{child_id}/consent',
                            json={'allow_achievement_sharing': False})
        body = parent_client.get(f'/api/parent/children/{child_id}/achievements').get_json()
        self.assertTrue(body.get('sharing_disabled'))
        self.assertEqual(body.get('achievements'), [])

    # --- H3 ---------------------------------------------------------------

    def test_h3_link_code_is_single_use_for_one_parent(self):
        app = self.create_app()
        student_client, _ = self.register_student(app, 'kid3@example.com', '+7 (912) 000-00-13')
        parent_a, _child_id, code = self.register_parent_and_link(app, student_client, 'pa@example.com')

        # a SECOND parent tries to redeem the SAME code -> rejected
        parent_b = app.test_client()
        parent_b.post('/api/auth/register', json={'email': 'pb@example.com', 'role': 'parent'})
        parent_b.patch('/api/users/me', json={'full_name': 'Parent B', 'phone': '+7 (912) 444-55-66'})
        redeem = parent_b.post('/api/parent/children/link', json={'code': code})
        self.assertEqual(redeem.status_code, 400, redeem.get_json())
        # parent B has no children
        self.assertEqual(parent_b.get('/api/parent/children').get_json()['children'], [])

    # --- H4 ---------------------------------------------------------------

    def test_h4_delete_user_with_dependencies_succeeds(self):
        app = self.create_app(enforce_fk=True)
        superadmin_id = self.make_user(app, email='root@example.com', role='superadmin', full_name='Root')
        teacher_id = self.make_user(app, email='teacher@example.com', role='teacher', full_name='Teach')
        parent_id = self.make_user(app, email='par@example.com', role='parent', full_name='Par')
        student_id = self.make_user(app, email='stud@example.com', role='student', full_name='Stud')

        # give the student a web of dependent rows that previously blocked deletion
        with app.app_context():
            from app.core.db import db
            from app.models.learning import Classroom
            from app.models.support import SupportTicket
            from app.models.staff_messaging import StaffDirectThread, StaffDirectMessage
            from app.models.parent_cabinet import (
                ParentChildLink, ParentConsentSettings, ParentSafetySettings,
                ParentTeacherThread, ParentTeacherMessage, ParentTeacherReadState,
            )

            classroom = Classroom(name='C', description='d', code='AUDIT1', teacher_id=teacher_id)
            db.session.add(classroom)
            db.session.add(SupportTicket(user_id=student_id, category='bug', subject='s', description='d'))
            db.session.add(ParentChildLink(parent_user_id=parent_id, child_user_id=student_id))
            db.session.add(ParentConsentSettings(parent_user_id=parent_id, child_user_id=student_id))
            db.session.add(ParentSafetySettings(parent_user_id=parent_id, child_user_id=student_id))
            low, high = sorted([student_id, superadmin_id])
            sd = StaffDirectThread(user_low_id=low, user_high_id=high)
            db.session.add(sd)
            db.session.flush()
            db.session.add(StaffDirectMessage(thread_id=sd.id, sender_id=superadmin_id, body='hi'))
            db.session.flush()
            ptt = ParentTeacherThread(
                parent_user_id=parent_id, teacher_id=teacher_id,
                child_user_id=student_id, classroom_id=classroom.id,
            )
            db.session.add(ptt)
            db.session.flush()
            db.session.add(ParentTeacherMessage(thread_id=ptt.id, sender_id=teacher_id, body='hello'))
            db.session.add(ParentTeacherReadState(thread_id=ptt.id, user_id=parent_id))
            db.session.commit()

        superadmin_client = self.client_for(app, 'root@example.com')
        resp = superadmin_client.delete(f'/api/admin/users/{student_id}')
        self.assertEqual(resp.status_code, 200, resp.get_json())

        with app.app_context():
            from app.core.db import db
            from app.models.user import User
            from app.models.support import SupportTicket
            from app.models.parent_cabinet import ParentChildLink

            self.assertIsNone(db.session.get(User, student_id))
            self.assertEqual(SupportTicket.query.filter_by(user_id=student_id).count(), 0)
            self.assertEqual(ParentChildLink.query.filter_by(child_user_id=student_id).count(), 0)

    # --- H5 ---------------------------------------------------------------

    def test_h5_staff_cannot_approve_own_bug_report(self):
        app = self.create_app()
        self.make_user(app, email='admin5@example.com', role='admin', full_name='Adm')
        admin_client = self.client_for(app, 'admin5@example.com')

        # the bug-report endpoint reads multipart form fields (it accepts a screenshot)
        created = admin_client.post('/api/support/bug-reports', data={
            'description': 'Self-filed report for XP farming attempt.',
            'reproduction_steps': 'Step 1, step 2, step 3.',
            'user_journey_path': '/dashboard',
        }, content_type='multipart/form-data')
        self.assertEqual(created.status_code, 201, created.get_json())
        report_id = created.get_json()['report']['id']

        # set a non-zero reward, then try to approve own report
        admin_client.patch('/api/support/staff/bug-hunter/settings', json={'approved_xp': 5000})
        approve = admin_client.patch(f'/api/support/staff/bug-reports/{report_id}',
                                     json={'moderation_status': 'approved'})
        self.assertEqual(approve.status_code, 403, approve.get_json())

    # --- H6 ---------------------------------------------------------------

    def test_h6_cannot_resubmit_checked_assignment(self):
        app = self.create_app()
        teacher_id = self.make_user(app, email='t6@example.com', role='teacher', full_name='T6')
        student_id = self.make_user(app, email='s6@example.com', role='student', full_name='S6')

        with app.app_context():
            from app.core.db import db
            from app.models.learning import (
                Assignment, AssignmentSubmission, ClassMembership, Classroom,
            )
            classroom = Classroom(name='C6', description='d', code='AUDIT6', teacher_id=teacher_id)
            db.session.add(classroom)
            db.session.flush()
            db.session.add(ClassMembership(classroom_id=classroom.id, student_id=student_id))
            assignment = Assignment(classroom_id=classroom.id, title='A6', description='p', difficulty='medium', xp_reward=50)
            db.session.add(assignment)
            db.session.flush()
            db.session.add(AssignmentSubmission(
                assignment_id=assignment.id, student_id=student_id,
                answer='graded answer', score=100, status='checked',
            ))
            db.session.commit()
            assignment_id = assignment.id

        student_client = self.client_for(app, 's6@example.com')
        resp = student_client.post(f'/api/assignments/{assignment_id}/submit', json={'answer': 'sneaky overwrite'})
        self.assertEqual(resp.status_code, 409, resp.get_json())

        # the graded submission is untouched
        with app.app_context():
            from app.models.learning import AssignmentSubmission
            sub = AssignmentSubmission.query.filter_by(assignment_id=assignment_id, student_id=student_id).first()
            self.assertEqual(sub.status, 'checked')
            self.assertEqual(sub.answer, 'graded answer')


if __name__ == '__main__':
    unittest.main()
