from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import case, func, or_
from werkzeug.exceptions import NotFound

from ..core.db import db
from ..core.gamification import level_from_xp
from ..core.pagination import DEFAULT_PAGE_SIZE, paginate_query, pagination_payload
from ..models.learning import (
    Assignment,
    AssignmentSubmission,
    ASSIGNMENT_META_PREFIX,
    ClassMembership,
    Classroom,
    UserProgress,
    decode_assignment_description,
)
from ..models.user import User

REVIEWED_SUBMISSION_STATUSES = {'checked', 'needs_revision'}
_TEACHER_REVIEWED_STATUSES_SQL = ('checked', 'needs_revision')


@dataclass(frozen=True)
class AssignmentStats:
    submissions_count: int = 0
    checked_count: int = 0


class TeacherQueryService:
    def __init__(self, session=None):
        self.session = session or db.session

    def _teacher_classes(
        self,
        teacher_id: int,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Classroom], dict]:
        query = (
            Classroom.query
            .filter_by(teacher_id=teacher_id)
            .order_by(Classroom.created_at.desc(), Classroom.id.desc())
        )
        return paginate_query(query, page=page, page_size=page_size)

    def _class_member_counts(self, class_ids: list[int]) -> dict[int, int]:
        if not class_ids:
            return {}
        rows = (
            self.session.query(
                ClassMembership.classroom_id,
                func.count(ClassMembership.id),
            )
            .filter(ClassMembership.classroom_id.in_(class_ids))
            .group_by(ClassMembership.classroom_id)
            .all()
        )
        return {classroom_id: count for classroom_id, count in rows}

    def _assignment_stats_map(self, assignment_ids: list[int]) -> dict[int, AssignmentStats]:
        if not assignment_ids:
            return {}
        rows = (
            self.session.query(
                AssignmentSubmission.assignment_id,
                func.count(AssignmentSubmission.id).label('submissions_count'),
                func.sum(
                    case(
                        (AssignmentSubmission.status.in_(REVIEWED_SUBMISSION_STATUSES), 1),
                        else_=0,
                    )
                ).label('checked_count'),
            )
            .filter(AssignmentSubmission.assignment_id.in_(assignment_ids))
            .group_by(AssignmentSubmission.assignment_id)
            .all()
        )
        return {
            assignment_id: AssignmentStats(
                submissions_count=int(submissions_count or 0),
                checked_count=int(checked_count or 0),
            )
            for assignment_id, submissions_count, checked_count in rows
        }

    @staticmethod
    def _practice_assignment_filter():
        return or_(
            Assignment.description.is_(None),
            ~Assignment.description.startswith(ASSIGNMENT_META_PREFIX),
            Assignment.description.like('%"assignment_type": "lesson_practice"%'),
        )

    def _practice_review_heatmap(
        self,
        classroom_id: int,
        assignments: list[Assignment],
    ) -> dict:
        """lesson_practice only: failures = needs_revision; denominator = checked + needs_revision."""
        practice_assignments: list[Assignment] = []
        for assignment in assignments:
            meta, _ = decode_assignment_description(assignment.description)
            if meta.get('assignment_type') != 'lesson_practice':
                continue
            practice_assignments.append(assignment)

        practice_ids = [a.id for a in practice_assignments]
        aggregated = (
            self.session.query(
                AssignmentSubmission.assignment_id,
                func.sum(case((AssignmentSubmission.status == 'needs_revision', 1), else_=0)).label(
                    'failed'
                ),
                func.sum(
                    case(
                        (AssignmentSubmission.status.in_(_TEACHER_REVIEWED_STATUSES_SQL), 1),
                        else_=0,
                    )
                ).label('reviewed'),
            )
            .filter(AssignmentSubmission.assignment_id.in_(practice_ids))
            .group_by(AssignmentSubmission.assignment_id)
            .all()
            if practice_ids
            else []
        )
        agg_map = {
            aid: (int(failed or 0), int(reviewed or 0)) for aid, failed, reviewed in aggregated
        }

        failed_total, reviewed_total = (
            self.session.query(
                func.sum(case((AssignmentSubmission.status == 'needs_revision', 1), else_=0)),
                func.sum(
                    case(
                        (AssignmentSubmission.status.in_(_TEACHER_REVIEWED_STATUSES_SQL), 1),
                        else_=0,
                    )
                ),
            )
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(
                Assignment.classroom_id == classroom_id,
                self._practice_assignment_filter(),
            )
            .one()
        )
        failed_total = int(failed_total or 0)
        reviewed_total = int(reviewed_total or 0)
        items: list[dict] = []
        for assignment in practice_assignments:
            failed, reviewed = agg_map.get(assignment.id, (0, 0))
            rate = round(100.0 * failed / reviewed, 1) if reviewed else None
            items.append(
                {
                    'assignment_id': assignment.id,
                    'title': assignment.title,
                    'failed': failed,
                    'reviewed': reviewed,
                    'failure_rate': rate,
                }
            )

        summary_rate = round(100.0 * failed_total / reviewed_total, 1) if reviewed_total else None
        return {
            'summary': {
                'failed': failed_total,
                'reviewed': reviewed_total,
                'failure_rate': summary_rate,
            },
            'assignments': items,
        }

    def _assignment_payload(self, assignment: Assignment, stats: AssignmentStats | None = None) -> dict:
        summary = stats or AssignmentStats()
        return {
            **assignment.to_dict(),
            'submissions_count': summary.submissions_count,
            'checked_count': summary.checked_count,
        }

    def _assignment_summary(self, classroom_id: int) -> dict:
        pending, reviewed = (
            self.session.query(
                func.sum(
                    case(
                        (~AssignmentSubmission.status.in_(_TEACHER_REVIEWED_STATUSES_SQL), 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (AssignmentSubmission.status.in_(_TEACHER_REVIEWED_STATUSES_SQL), 1),
                        else_=0,
                    )
                ),
            )
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .filter(Assignment.classroom_id == classroom_id)
            .one()
        )
        today = datetime.now(UTC).date().isoformat()
        overdue = (
            self.session.query(func.count(Assignment.id))
            .filter(
                Assignment.classroom_id == classroom_id,
                Assignment.due_date.is_not(None),
                Assignment.due_date != '',
                Assignment.due_date < today,
            )
            .scalar()
            or 0
        )
        return {
            'pending_submissions': int(pending or 0),
            'reviewed_submissions': int(reviewed or 0),
            'overdue_assignments': int(overdue),
        }

    def _order_assignments_for_review(self, query):
        pending_count = (
            self.session.query(func.count(AssignmentSubmission.id))
            .filter(
                AssignmentSubmission.assignment_id == Assignment.id,
                ~AssignmentSubmission.status.in_(_TEACHER_REVIEWED_STATUSES_SQL),
            )
            .correlate(Assignment)
            .scalar_subquery()
        )
        due_date_missing = case(
            (or_(Assignment.due_date.is_(None), Assignment.due_date == ''), 1),
            else_=0,
        )
        return query.order_by(
            pending_count.desc(),
            due_date_missing.asc(),
            Assignment.due_date.asc(),
            Assignment.created_at.desc(),
            Assignment.id.desc(),
        )

    def _classroom_payload(
        self,
        classroom: Classroom,
        *,
        students_count: int = 0,
        assignments_count: int = 0,
    ) -> dict:
        return {
            'id': classroom.id,
            'name': classroom.name,
            'description': classroom.description,
            'code': classroom.code,
            'teacher_id': classroom.teacher_id,
            'students_count': students_count,
            'assignments_count': assignments_count,
        }

    def classes_payload(
        self,
        teacher: User,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        classes, pagination = self._teacher_classes(
            teacher.id,
            page=page,
            page_size=page_size,
        )
        return {
            'classes': [item.to_dict() for item in classes],
            'pagination': pagination,
        }

    def overview_payload(
        self,
        teacher: User,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        classes, classes_pagination = self._teacher_classes(
            teacher.id,
            page=page,
            page_size=page_size,
        )
        class_ids = [item.id for item in classes]
        member_counts = self._class_member_counts(class_ids)

        assignment_count_rows = (
            self.session.query(Assignment.classroom_id, func.count(Assignment.id))
            .filter(Assignment.classroom_id.in_(class_ids))
            .group_by(Assignment.classroom_id)
            .all()
            if class_ids
            else []
        )
        assignments_per_class = {classroom_id: count for classroom_id, count in assignment_count_rows}
        total_students = (
            self.session.query(func.count(ClassMembership.id))
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .filter(Classroom.teacher_id == teacher.id)
            .scalar()
            or 0
        )
        total_assignments = (
            self.session.query(func.count(Assignment.id))
            .join(Classroom, Classroom.id == Assignment.classroom_id)
            .filter(Classroom.teacher_id == teacher.id)
            .scalar()
            or 0
        )
        total_submissions = (
            self.session.query(func.count(AssignmentSubmission.id))
            .join(Assignment, Assignment.id == AssignmentSubmission.assignment_id)
            .join(Classroom, Classroom.id == Assignment.classroom_id)
            .filter(Classroom.teacher_id == teacher.id)
            .scalar()
            or 0
        )

        return {
            'summary': {
                'classes': classes_pagination['total'],
                'students': int(total_students),
                'assignments': int(total_assignments),
                'submissions': int(total_submissions),
            },
            'classes': [
                self._classroom_payload(
                    classroom,
                    students_count=member_counts.get(classroom.id, 0),
                    assignments_count=assignments_per_class.get(classroom.id, 0),
                )
                for classroom in classes
            ],
            'classes_pagination': classes_pagination,
        }

    def class_detail_payload(
        self,
        teacher: User,
        classroom_id: int,
        *,
        students_page: int = 1,
        assignments_page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        classroom = Classroom.query.filter_by(id=classroom_id, teacher_id=teacher.id).first_or_404()
        assignments_query = self._order_assignments_for_review(
            Assignment.query.filter_by(classroom_id=classroom.id)
        )
        assignments, assignments_pagination = paginate_query(
            assignments_query,
            page=assignments_page,
            page_size=page_size,
        )
        assignment_stats = self._assignment_stats_map([assignment.id for assignment in assignments])
        students_total = ClassMembership.query.filter_by(classroom_id=classroom.id).count()
        student_query = (
            self.session.query(
                ClassMembership.student_id,
                User.email,
                User.full_name,
                User.xp,
                func.count(
                    case((UserProgress.status == 'completed', UserProgress.id), else_=None)
                ).label('completed_lessons'),
                func.avg(
                    case((UserProgress.status == 'completed', UserProgress.score), else_=None)
                ).label('average_score'),
            )
            .join(User, User.id == ClassMembership.student_id)
            .outerjoin(UserProgress, UserProgress.user_id == ClassMembership.student_id)
            .filter(ClassMembership.classroom_id == classroom.id)
            .group_by(ClassMembership.student_id, User.email, User.full_name, User.xp)
            .order_by(User.full_name.asc(), User.email.asc(), ClassMembership.student_id.asc())
        )
        student_rows = student_query.offset((students_page - 1) * page_size).limit(page_size).all()

        students = [
            {
                'id': student_id,
                'email': email,
                'full_name': full_name,
                'xp': xp,
                'level': level_from_xp(xp),
                'completed_lessons': int(completed_lessons or 0),
                'average_score': round(float(average_score or 0), 1),
            }
            for student_id, email, full_name, xp, completed_lessons, average_score in student_rows
        ]

        return {
            'classroom': self._classroom_payload(
                classroom,
                students_count=students_total,
                assignments_count=assignments_pagination['total'],
            ),
            'students': students,
            'students_pagination': pagination_payload(students_total, students_page, page_size),
            'assignments': [
                self._assignment_payload(assignment, assignment_stats.get(assignment.id))
                for assignment in assignments
            ],
            'assignments_pagination': assignments_pagination,
            'assignment_summary': self._assignment_summary(classroom.id),
            'practice_heatmap': self._practice_review_heatmap(classroom.id, assignments),
        }

    def class_assignments_payload(
        self,
        teacher: User,
        classroom_id: int,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        classroom = Classroom.query.filter_by(id=classroom_id, teacher_id=teacher.id).first_or_404()
        query = self._order_assignments_for_review(
            Assignment.query.filter_by(classroom_id=classroom.id)
        )
        assignments, pagination = paginate_query(query, page=page, page_size=page_size)
        stats_map = self._assignment_stats_map([assignment.id for assignment in assignments])
        return {
            'assignments': [
                self._assignment_payload(assignment, stats_map.get(assignment.id))
                for assignment in assignments
            ],
            'pagination': pagination,
        }

    def assignment_submissions_payload(
        self,
        teacher: User,
        assignment_id: int,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        status: str = 'all',
    ) -> dict:
        assignment = db.session.get(Assignment, assignment_id)
        if assignment is None:
            raise NotFound()
        if assignment.classroom.teacher_id != teacher.id:
            raise PermissionError('Forbidden')

        query = (
            AssignmentSubmission.query
            .filter_by(assignment_id=assignment.id)
            .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        )
        if status == 'pending':
            query = query.filter(
                AssignmentSubmission.status.in_(('submitted', 'pending_review'))
            )
        elif status != 'all':
            query = query.filter(AssignmentSubmission.status == status)
        submissions, pagination = paginate_query(query, page=page, page_size=page_size)
        stats = self._assignment_stats_map([assignment.id]).get(assignment.id, AssignmentStats())
        return {
            'assignment': self._assignment_payload(assignment, stats),
            'submissions': [submission.to_dict() for submission in submissions],
            'pagination': pagination,
        }
