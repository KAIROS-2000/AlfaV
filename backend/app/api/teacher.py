from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, request
from sqlalchemy import or_
from sqlalchemy.orm.exc import StaleDataError

from ..core.db import db
from ..core.pagination import paginate_query, pagination_params
from .lesson_builder import build_lesson_quiz
from ..core.security import auth_required
from ..models.learning import (
    Assignment,
    AssignmentSubmission,
    ClassJoinRequest,
    ClassMembership,
    Classroom,
    CUSTOM_CLASSROOM_MODULE_PREFIX,
    Lesson,
    Module,
    Task,
    UserProgress,
    age_group_supports_code,
    build_custom_classroom_module_slug,
    custom_classroom_module_slug_prefix,
    encode_assignment_description,
    has_explicit_code_task_intent,
    lesson_publish_readiness_errors,
    normalize_assignment_type,
    normalize_submission_format,
    normalize_task_validation,
    normalize_authoring_metadata,
    clone_lesson_content,
)
from ..models.user import User, UserRole
from ..services import notifications, parent_messaging
from ..services.teacher_query_service import TeacherQueryService
from ..seed.bootstrap import generate_code


teacher_bp = Blueprint('teacher', __name__)
VALID_AGE_GROUPS = {'junior', 'middle', 'senior'}
VALID_DIFFICULTIES = {'easy', 'medium', 'hard'}
VALID_SUBMISSION_REVIEW_STATUSES = {'checked', 'needs_revision'}
VALID_SUBMISSION_LIST_STATUSES = {
    'all',
    'pending',
    'submitted',
    'pending_review',
    *VALID_SUBMISSION_REVIEW_STATUSES,
}
VALID_JOIN_REQUEST_STATUSES = {'pending', 'approved', 'rejected'}
VALID_LESSON_LIST_STATUSES = {'all', 'draft', 'published', 'archived'}
VALID_CATALOG_SOURCES = {'all', 'catalog', 'teacher'}
ASSIGNMENT_TYPE_DEFAULT_TITLES = {
    'lesson_practice': 'Практика по уроку',
    'mini_project': 'Мини-проект',
    'quiz': 'Тест по теме',
    'reflection': 'Рефлексия по теме',
}
ASSIGNMENT_TYPE_DEFAULT_DESCRIPTIONS = {
    'lesson_practice': 'Повтори ключевые шаги урока и покажи решение.',
    'mini_project': 'Создай мини-проект по теме и опиши, как он работает.',
    'quiz': 'Пройди короткий тест и обоснуй ответы на сложные вопросы.',
    'reflection': 'Коротко опиши, что получилось, что было сложно и что стоит улучшить.',
}
ASSIGNMENT_REQUIRED_FIELD_LABELS = {
    'title': 'название задания',
    'lesson_id': 'урок',
    'due_date': 'дедлайн',
    'learning_goal': 'цель обучения',
    'resources': 'материалы',
    'work_steps': 'шаги выполнения',
    'success_criteria': 'критерии успеха',
    'description': 'описание задания',
}
CLASS_REQUIRED_FIELD_LABELS = {
    'name': 'название класса',
}
LESSON_REQUIRED_FIELD_LABELS = {
    'title': 'название урока',
    'summary': 'краткое описание урока',
    'duration_minutes': 'длительность урока',
    'passing_score': 'минимальный результат для прохождения',
    'theory_text': 'объяснение темы',
    'key_points': 'ключевые идеи',
    'interactive_steps': 'маршрут урока',
    'task_title': 'название практики',
    'task_prompt': 'формулировка задания',
    'starter_code': 'стартовый код',
    'answer_keywords': 'ключевые слова для автопроверки',
    'judge_tests': 'автотесты',
}


def _teacher_class_ids(current_user: User) -> list[int]:
    return [row[0] for row in Classroom.query.with_entities(Classroom.id).filter_by(teacher_id=current_user.id).all()]


def _teacher_join_request_or_404(current_user: User, request_id: int) -> ClassJoinRequest:
    return (
        ClassJoinRequest.query.join(Classroom)
        .filter(ClassJoinRequest.id == request_id, Classroom.teacher_id == current_user.id)
        .first_or_404()
    )


def _safe_int(value, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def _is_draft_save(data: dict) -> bool:
    """Only an explicit JSON boolean opens the incomplete draft-save path."""
    return data.get('save_draft') is True


def _draft_payload_from_request(data: dict) -> dict:
    raw_payload = data.get('draft_payload')
    if isinstance(raw_payload, dict):
        return raw_payload
    return {
        key: data[key]
        for key in (
            'title', 'summary', 'age_group', 'content_format', 'duration_minutes',
            'passing_score', 'theory_text', 'key_points', 'interactive_steps',
            'practice_enabled', 'task_type', 'task_title', 'task_prompt',
            'task_hints', 'evaluation_mode', 'answer_keywords', 'starter_code',
            'programming_language', 'judge_tests', 'time_limit_ms',
            'memory_limit_mb', 'task', 'quiz',
        )
        if key in data
    }


def _is_complete_builder_payload(data: dict) -> bool:
    has_task_payload = 'task' in data or 'practice_enabled' in data
    return has_task_payload and all(
        field in data
        for field in (
            'title', 'summary', 'content_format', 'duration_minutes',
            'passing_score', 'theory_text', 'key_points', 'interactive_steps',
            'quiz',
        )
    )


def _authoring_metadata_for_write(lesson: Lesson, data: dict) -> dict:
    metadata = normalize_authoring_metadata(lesson.authoring_metadata)
    if isinstance(data.get('authoring_metadata'), dict):
        metadata = normalize_authoring_metadata(data['authoring_metadata'])
    if 'format_note' in data:
        metadata['format_note'] = str(data.get('format_note') or '').strip()
    if _is_draft_save(data):
        if 'draft_payload' in data and not isinstance(data.get('draft_payload'), dict):
            raise ValueError('Черновик должен содержать JSON-объект размером не более 64 КБ.')
        metadata['draft_payload'] = _draft_payload_from_request(data)
    elif _is_complete_builder_payload(data):
        metadata.pop('draft_payload', None)

    normalized = normalize_authoring_metadata(metadata)
    if _is_draft_save(data) and 'draft_payload' not in normalized:
        raise ValueError('Черновик должен содержать JSON-объект размером не более 64 КБ.')
    return normalized


def _lesson_list_status_from_request() -> str | None:
    raw_status = request.args.get('status')
    status = 'all' if raw_status is None else raw_status.strip().lower()
    return status if status in VALID_LESSON_LIST_STATUSES else None


def _filter_lessons_by_status(query, status: str):
    if status == 'draft':
        return query.filter(Lesson.is_published.is_(False), Lesson.archived_at.is_(None))
    if status == 'published':
        return query.filter(Lesson.is_published.is_(True), Lesson.archived_at.is_(None))
    if status == 'archived':
        return query.filter(Lesson.archived_at.is_not(None))
    return query


def _parse_positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_text(value) -> bool:
    return bool(str(value or '').strip())


def _has_int_value(value) -> bool:
    return _parse_int(value) is not None


def _normalize_age_group(value: str | None) -> str:
    normalized = (value or 'middle').strip().lower()
    return normalized if normalized in VALID_AGE_GROUPS else 'middle'


def _normalize_difficulty(value: str | None) -> str:
    normalized = (value or 'medium').strip().lower()
    return normalized if normalized in VALID_DIFFICULTIES else 'medium'


def _split_lines(value) -> list[str]:
    if isinstance(value, list):
        return [str(item or '').strip() for item in value if str(item or '').strip()]
    return [item.strip() for item in str(value or '').splitlines() if item.strip()]


def _split_csv(value) -> list[str]:
    if isinstance(value, list):
        return [str(item or '').strip() for item in value if str(item or '').strip()]
    return [item.strip() for item in str(value or '').replace('\n', ',').split(',') if item.strip()]


def _normalize_due_date(value: str | None) -> str | None:
    normalized = (value or '').strip()
    return normalized or None


def _normalize_submission_review_status(value: str | None) -> str:
    normalized = (value or 'checked').strip().lower()
    return normalized if normalized in VALID_SUBMISSION_REVIEW_STATUSES else 'checked'


def _complete_judge_tests(value) -> list[dict]:
    if not isinstance(value, list):
        return []

    tests: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        expected = str(
            item.get('expected')
            if item.get('expected') is not None
            else item.get('stdout') or ''
        )
        # Empty stdin is a valid test case (programs often read no input), but
        # a judge test still needs an expected result.
        if expected:
            tests.append(item)
    return tests


def _has_partial_judge_test(value) -> bool:
    if not isinstance(value, list):
        return False

    for item in value:
        if not isinstance(item, dict):
            continue
        expected = str(
            item.get('expected')
            if item.get('expected') is not None
            else item.get('stdout') or ''
        )
        if not expected:
            return True
    return False


def _lesson_practice_requested(data: dict) -> bool:
    if 'practice_enabled' in data:
        return bool(data.get('practice_enabled'))
    return any(
        [
            _has_text(data.get('task_title')),
            _has_text(data.get('task_prompt')),
            _has_text(data.get('starter_code')),
            bool(_split_csv(data.get('answer_keywords'))),
            bool(data.get('judge_tests')),
        ]
    )


def _compose_assignment_description(data: dict, assignment_type: str) -> str:
    summary = (data.get('description') or '').strip()
    goal = (data.get('learning_goal') or '').strip()
    criteria = _split_lines(data.get('success_criteria'))
    steps = _split_lines(data.get('work_steps'))
    resources = _split_lines(data.get('resources'))

    sections: list[str] = []
    if summary:
        sections.append(summary)
    else:
        sections.append(ASSIGNMENT_TYPE_DEFAULT_DESCRIPTIONS[assignment_type])

    if goal:
        sections.append(f'Цель: {goal}')
    if steps:
        sections.append('Шаги выполнения:\n' + '\n'.join(f'- {item}' for item in steps))
    if criteria:
        sections.append('Критерии успеха:\n' + '\n'.join(f'- {item}' for item in criteria))
    if resources:
        sections.append('Материалы:\n' + '\n'.join(f'- {item}' for item in resources))

    return '\n\n'.join(sections).strip()


def _missing_assignment_fields(data: dict) -> list[str]:
    missing: list[str] = []

    for field in (
        'title',
        'due_date',
        'learning_goal',
        'resources',
        'work_steps',
        'success_criteria',
        'description',
    ):
        if not (data.get(field) or '').strip():
            missing.append(field)

    lesson_id = data.get('lesson_id')
    if lesson_id is None or (isinstance(lesson_id, str) and not lesson_id.strip()):
        missing.append('lesson_id')

    return missing


def _missing_class_fields(data: dict) -> list[str]:
    return ['name'] if not _has_text(data.get('name')) else []


def _missing_lesson_fields(data: dict) -> list[str]:
    missing: list[str] = []

    for field in ('title', 'summary', 'theory_text'):
        if not _has_text(data.get(field)):
            missing.append(field)

    if not _has_int_value(data.get('duration_minutes')):
        missing.append('duration_minutes')
    if not _has_int_value(data.get('passing_score')):
        missing.append('passing_score')
    if len(_split_lines(data.get('key_points')) or _split_csv(data.get('key_points'))) < 2:
        missing.append('key_points')
    if len(_split_lines(data.get('interactive_steps'))) < 2:
        missing.append('interactive_steps')

    if not _lesson_practice_requested(data):
        return missing

    requested_task_type = 'code' if (data.get('task_type') or '').strip().lower() == 'code' else 'text'
    evaluation_mode = (data.get('evaluation_mode') or '').strip().lower()
    needs_tests = requested_task_type == 'code' or evaluation_mode == 'stdin_stdout'

    if not _has_text(data.get('task_title')):
        missing.append('task_title')
    if not _has_text(data.get('task_prompt')):
        missing.append('task_prompt')
    if requested_task_type == 'code' and not _has_text(data.get('starter_code')):
        missing.append('starter_code')
    if evaluation_mode == 'keywords' and not _split_csv(data.get('answer_keywords')):
        missing.append('answer_keywords')
    if needs_tests and (
        not _complete_judge_tests(data.get('judge_tests'))
        or _has_partial_judge_test(data.get('judge_tests'))
    ):
        missing.append('judge_tests')

    return missing


def _get_or_create_custom_module(classroom: Classroom, age_group: str) -> Module:
    slug = build_custom_classroom_module_slug(classroom.id, age_group)
    module = Module.query.filter_by(slug=slug).first()
    if module:
        return module

    module = Module(
        slug=slug,
        title=f'Уроки класса {classroom.name}',
        description=f'Авторские уроки для класса {classroom.name}',
        age_group=age_group,
        icon='book-open',
        color='#0EA5E9',
        order_index=Module.query.count() + 1,
        is_published=False,
    )
    db.session.add(module)
    db.session.flush()
    return module


def _teacher_can_use_lesson(classroom: Classroom, lesson: Lesson) -> bool:
    if lesson.module.is_published and lesson.is_published and lesson.archived_at is None:
        return True
    return lesson.module.custom_classroom_id == classroom.id and lesson.is_published and lesson.archived_at is None


def _lesson_catalog_item(lesson: Lesson) -> dict:
    return {
        **lesson.to_summary_dict(),
        'lesson_url': f'/lessons/{lesson.id}',
        'module_age_group': lesson.module.age_group,
        'source': 'teacher' if lesson.module.is_custom_classroom_module else 'catalog',
        'source_label': 'Урок учителя' if lesson.module.is_custom_classroom_module else 'Библиотека уроков',
    }


def _catalog_lessons_for_teacher(
    current_user: User,
    classroom: Classroom | None = None,
    *,
    source: str = 'all',
    search: str = '',
):
    classroom_ids = [classroom.id] if classroom else _teacher_class_ids(current_user)
    public_filter = (
        Module.is_published.is_(True)
        & Module.slug.notlike(f'{CUSTOM_CLASSROOM_MODULE_PREFIX}%')
    )
    teacher_filters = [
        Module.slug.like(f'{custom_classroom_module_slug_prefix(classroom_id)}%')
        for classroom_id in classroom_ids
    ]
    if source == 'catalog':
        visibility_filter = public_filter
    elif source == 'teacher':
        visibility_filter = or_(*teacher_filters) if teacher_filters else Module.id.is_(None)
    else:
        visibility_filter = or_(public_filter, *teacher_filters)

    query = Lesson.query.join(Module).filter(
        visibility_filter,
        Lesson.is_published.is_(True),
        Lesson.archived_at.is_(None),
    )
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(
            Lesson.title.ilike(pattern),
            Lesson.summary.ilike(pattern),
            Module.title.ilike(pattern),
        ))
    return query.order_by(
        Module.is_published.desc(),
        Module.title.asc(),
        Module.id.asc(),
        Lesson.order_index.asc(),
        Lesson.id.asc(),
    )


def _teacher_owns_lesson(current_user: User, lesson: Lesson) -> bool:
    classroom_id = lesson.module.custom_classroom_id
    return bool(
        classroom_id
        and Classroom.query.filter_by(id=classroom_id, teacher_id=current_user.id).first()
    )


def _teacher_lesson_or_404(current_user: User, lesson_id: int) -> Lesson:
    lesson = db.get_or_404(Lesson, lesson_id)
    if not _teacher_owns_lesson(current_user, lesson):
        from flask import abort
        abort(403)
    return lesson


def _build_teacher_theory_blocks(
    title: str, summary: str, theory_text: str, key_points: list[str]
) -> list[dict]:
    blocks = [{'type': 'hero', 'title': title, 'text': summary}]
    if theory_text:
        blocks.append({'type': 'text', 'title': 'Объяснение', 'text': theory_text})
    if key_points:
        blocks.append({'type': 'list', 'title': 'Ключевые идеи', 'items': key_points})
    return blocks


def _build_teacher_interactive_steps(raw_steps) -> list[dict]:
    return [
        {'title': f'Шаг {index}', 'text': item}
        for index, item in enumerate(_split_lines(raw_steps), start=1)
    ]


def _flat_task_payload(raw_task: dict) -> dict:
    """Translate the shared builder's nested task into the teacher create shape."""
    return {
        'practice_enabled': raw_task.get('enabled') is True,
        'task_type': raw_task.get('task_type'),
        'task_title': raw_task.get('title'),
        'task_prompt': raw_task.get('prompt'),
        'task_hints': raw_task.get('hints'),
        'evaluation_mode': raw_task.get('evaluation_mode'),
        'answer_keywords': raw_task.get('keywords'),
        'starter_code': raw_task.get('starter_code'),
        'programming_language': raw_task.get('language'),
        'judge_tests': raw_task.get('tests'),
        'time_limit_ms': raw_task.get('time_limit_ms'),
        'memory_limit_mb': raw_task.get('memory_limit_mb'),
        'xp_reward': raw_task.get('xp_reward'),
    }


def _build_teacher_task(lesson: Lesson, data: dict) -> Task | None:
    task_title = str(data.get('task_title') or '').strip()
    task_prompt = str(data.get('task_prompt') or '').strip()
    starter_code = str(data.get('starter_code') or '')
    requested_task_type = 'code' if str(data.get('task_type') or '').strip().lower() == 'code' else 'text'
    requested_is_code_task = requested_task_type == 'code' or bool(starter_code.strip())
    practice_enabled = _lesson_practice_requested(data)
    answer_keywords = _split_csv(data.get('answer_keywords'))
    explicit_code_intent = has_explicit_code_task_intent(
        title=task_title,
        prompt=task_prompt,
        starter_code=starter_code,
    )
    if requested_task_type == 'text' and explicit_code_intent:
        raise ValueError('Задание выглядит как кодовая практика. Выберите формат "Код" и добавьте автотесты.')

    judge_tests = data.get('judge_tests')
    requested_code_runner = str(data.get('evaluation_mode') or '').strip().lower() == 'stdin_stdout' or bool(judge_tests)
    age_group = lesson.module.age_group
    if not age_group_supports_code(age_group) and (requested_is_code_task or requested_code_runner):
        raise ValueError('Для Junior-уроков кодовая практика недоступна. Используйте текстовое задание без стартового кода и автотестов.')
    if not practice_enabled:
        return None

    task_hints = _split_lines(data.get('task_hints')) or (
        [
            'Проверь, что программа читает входные данные из stdin.',
            'Сравни формат вывода с ожидаемым ответом посимвольно.',
            'Прогони решение на граничных примерах перед отправкой.',
        ]
        if requested_is_code_task
        else [
            'Сверь ответ с объяснением урока.',
            'Разбей решение на короткие шаги.',
            'Проверь, есть ли в ответе ключевые слова темы.',
        ]
    )
    task_validation = normalize_task_validation(
        {
            'evaluation_mode': data.get('evaluation_mode'),
            'language': data.get('programming_language'),
            'keywords': answer_keywords,
            'tests': judge_tests,
            'time_limit_ms': data.get('time_limit_ms'),
            'memory_limit_mb': data.get('memory_limit_mb'),
        },
        is_custom_lesson=True,
        task_type='code' if requested_is_code_task else 'text',
        age_group=age_group,
    )
    if requested_is_code_task and not task_validation['tests']:
        raise ValueError('Кодовая задача сохраняется только с автотестами. Добавьте хотя бы один тест с входом и ожидаемым выводом.')
    if task_validation['evaluation_mode'] == 'keywords' and not task_validation['keywords']:
        raise ValueError('Для автопроверки по ключевым словам добавьте хотя бы одно ключевое слово.')
    if task_validation['evaluation_mode'] == 'stdin_stdout' and not task_validation['tests']:
        raise ValueError('Для проверки кода добавьте хотя бы один тест с входом и ожидаемым выводом.')

    task_type = 'code' if requested_is_code_task or task_validation['evaluation_mode'] == 'stdin_stdout' else 'text'
    return Task(
        lesson_id=lesson.id,
        task_type=task_type,
        title=task_title or f'Практика: {lesson.title}',
        prompt=task_prompt or 'Выполни практическое задание по этому уроку.',
        starter_code=starter_code if task_type == 'code' else '',
        validation=task_validation,
        hints=task_hints,
        xp_reward=_safe_int(data.get('xp_reward'), 0, minimum=0, maximum=500),
    )


def _apply_teacher_lesson_changes(lesson: Lesson, data: dict) -> None:
    for field in ('title', 'summary', 'content_format'):
        if field in data:
            value = str(data.get(field) or '').strip()
            if value:
                setattr(lesson, field, value)
    for field, minimum, maximum in (
        ('duration_minutes', 5, 180),
        ('passing_score', 0, 100),
    ):
        if field in data:
            setattr(lesson, field, _safe_int(data[field], getattr(lesson, field), minimum=minimum, maximum=maximum))

    if 'theory_blocks' in data and isinstance(data['theory_blocks'], list):
        lesson.theory_blocks = data['theory_blocks']
    elif any(field in data for field in ('theory_text', 'key_points')):
        lesson.theory_blocks = _build_teacher_theory_blocks(
            lesson.title,
            lesson.summary,
            str(data.get('theory_text') or '').strip(),
            _split_lines(data.get('key_points')) or _split_csv(data.get('key_points')),
        )
    if 'interactive_steps' in data:
        raw_steps = data['interactive_steps']
        lesson.interactive_steps = (
            raw_steps
            if isinstance(raw_steps, list) and all(isinstance(item, dict) for item in raw_steps)
            else _build_teacher_interactive_steps(raw_steps)
        )

    lesson.authoring_metadata = _authoring_metadata_for_write(lesson, data)
    if _is_draft_save(data):
        return

    if 'task' in data:
        raw_task = data.get('task')
        if not isinstance(raw_task, dict):
            raw_task = {'enabled': False}
        task = _build_teacher_task(lesson, _flat_task_payload(raw_task))
        lesson.tasks.clear()
        if task is not None:
            lesson.tasks.append(task)
    elif 'practice_enabled' in data:
        task = _build_teacher_task(lesson, data)
        lesson.tasks.clear()
        if task is not None:
            lesson.tasks.append(task)
    elif 'tasks' in data and isinstance(data['tasks'], list):
        replacement_tasks: list[Task] = []
        for raw in data['tasks']:
            if not isinstance(raw, dict):
                continue
            task_type = 'code' if str(raw.get('task_type') or '').strip().lower() == 'code' else 'text'
            validation = normalize_task_validation(
                raw.get('validation'),
                is_custom_lesson=True,
                task_type=task_type,
                age_group=lesson.module.age_group,
            )
            replacement_tasks.append(Task(
                task_type=task_type,
                title=str(raw.get('title') or '').strip() or f'Практика: {lesson.title}',
                prompt=str(raw.get('prompt') or '').strip() or 'Выполни практическое задание по этому уроку.',
                starter_code=str(raw.get('starter_code') or '') if task_type == 'code' else '',
                validation=validation,
                hints=_split_lines(raw.get('hints')),
                xp_reward=_safe_int(raw.get('xp_reward'), 0, minimum=0, maximum=500),
            ))
        lesson.tasks.clear()
        lesson.tasks.extend(replacement_tasks)

    if 'quiz' in data:
        quiz = build_lesson_quiz(lesson, data.get('quiz'), lesson.title, question_prefix='teacher-q')
        lesson.quizzes.clear()
        if quiz is not None:
            lesson.quizzes.append(quiz)
    elif 'quizzes' in data and isinstance(data['quizzes'], list):
        replacement_quizzes = []
        for raw in data['quizzes']:
            if not isinstance(raw, dict):
                continue
            quiz = build_lesson_quiz(lesson, {**raw, 'enabled': True}, lesson.title, question_prefix='teacher-q')
            if quiz is not None:
                replacement_quizzes.append(quiz)
        lesson.quizzes.clear()
        lesson.quizzes.extend(replacement_quizzes)


def _check_lesson_version(lesson: Lesson, data: dict):
    try:
        expected = int(data.get('version'))
    except (TypeError, ValueError):
        return {'message': 'Укажите актуальную версию урока.', 'lesson': lesson.to_authoring_dict()}, 400
    if expected != lesson.version:
        return {'message': 'Урок уже изменён в другой вкладке.', 'lesson': lesson.to_authoring_dict()}, 409
    return None


def _check_optional_lesson_version(lesson: Lesson, data: dict):
    return _check_lesson_version(lesson, data) if 'version' in data else None


def _stale_lesson_write_response(lesson_id: int):
    db.session.rollback()
    current_lesson = db.session.get(Lesson, lesson_id)
    return {
        'message': 'Урок уже изменён в другой вкладке.',
        'lesson': current_lesson.to_authoring_dict() if current_lesson else None,
    }, 409


@teacher_bp.get('/overview')
@auth_required([UserRole.TEACHER])
def teacher_overview(current_user: User):
    page, page_size = pagination_params(request.args)
    return TeacherQueryService().overview_payload(
        current_user,
        page=page,
        page_size=page_size,
    )


@teacher_bp.post('/classes')
@auth_required([UserRole.TEACHER])
def create_class(current_user: User):
    data = request.get_json() or {}
    missing_fields = _missing_class_fields(data)
    if missing_fields:
        labels = ', '.join(CLASS_REQUIRED_FIELD_LABELS[field] for field in missing_fields)
        return {
            'message': f'Заполните обязательные поля: {labels}.',
            'fields': missing_fields,
        }, 400

    classroom = Classroom(
        name=str(data.get('name') or '').strip(),
        description=(data.get('description') or '').strip() or None,
        code=generate_code(),
        teacher_id=current_user.id,
    )
    db.session.add(classroom)
    db.session.commit()
    return {'classroom': classroom.to_dict()}, 201


@teacher_bp.get('/classes')
@auth_required([UserRole.TEACHER])
def list_classes(current_user: User):
    page, page_size = pagination_params(request.args)
    return TeacherQueryService().classes_payload(
        current_user,
        page=page,
        page_size=page_size,
    )


@teacher_bp.get('/join-requests')
@auth_required([UserRole.TEACHER])
def list_join_requests(current_user: User):
    status = (request.args.get('status') or 'pending').strip().lower()
    if status != 'all' and status not in VALID_JOIN_REQUEST_STATUSES:
        return {'message': 'Некорректный статус заявки.'}, 400

    query = ClassJoinRequest.query.join(Classroom).filter(
        Classroom.teacher_id == current_user.id
    )
    if status != 'all':
        query = query.filter(ClassJoinRequest.status == status)

    page, page_size = pagination_params(request.args)
    query = query.order_by(ClassJoinRequest.created_at.desc(), ClassJoinRequest.id.desc())
    join_requests, pagination = paginate_query(query, page=page, page_size=page_size)
    return {
        'requests': [item.to_dict() for item in join_requests],
        'pagination': pagination,
    }


@teacher_bp.post('/join-requests/<int:request_id>/approve')
@auth_required([UserRole.TEACHER])
def approve_join_request(current_user: User, request_id: int):
    join_request = _teacher_join_request_or_404(current_user, request_id)
    if join_request.status != 'pending':
        return {'message': 'Заявка уже обработана.'}, 400

    applicant = db.session.get(User, join_request.student_id)
    if not applicant or applicant.role != UserRole.STUDENT:
        return {'message': 'В класс могут вступать только ученики.'}, 400

    existing_membership = ClassMembership.query.filter_by(
        classroom_id=join_request.classroom_id,
        student_id=join_request.student_id,
    ).first()
    if not existing_membership:
        db.session.add(
            ClassMembership(
                classroom_id=join_request.classroom_id,
                student_id=join_request.student_id,
            )
        )

    join_request.status = 'approved'
    join_request.decided_at = datetime.now(UTC)
    join_request.decided_by_id = current_user.id
    db.session.commit()
    return {
        'message': 'Ученик добавлен в класс.',
        'request': join_request.to_dict(),
    }


@teacher_bp.post('/join-requests/<int:request_id>/reject')
@auth_required([UserRole.TEACHER])
def reject_join_request(current_user: User, request_id: int):
    join_request = _teacher_join_request_or_404(current_user, request_id)
    if join_request.status != 'pending':
        return {'message': 'Заявка уже обработана.'}, 400

    join_request.status = 'rejected'
    join_request.decided_at = datetime.now(UTC)
    join_request.decided_by_id = current_user.id
    db.session.commit()
    return {
        'message': 'Заявка отклонена.',
        'request': join_request.to_dict(),
    }


@teacher_bp.get('/classes/<int:classroom_id>')
@auth_required([UserRole.TEACHER])
def class_detail(current_user: User, classroom_id: int):
    students_page, page_size = pagination_params(
        request.args,
        page_key='students_page',
    )
    assignments_page, _ = pagination_params(
        request.args,
        page_key='assignments_page',
    )
    return TeacherQueryService().class_detail_payload(
        current_user,
        classroom_id,
        students_page=students_page,
        assignments_page=assignments_page,
        page_size=page_size,
    )


def _sync_lesson_progress_from_review(submission: AssignmentSubmission) -> None:
    lesson = submission.assignment.lesson
    if lesson is None or not lesson.module.is_custom_classroom_module:
        return

    progress = UserProgress.query.filter_by(user_id=submission.student_id, lesson_id=lesson.id).first()
    if progress is None:
        progress = UserProgress(user_id=submission.student_id, lesson_id=lesson.id, status='not_started')
        db.session.add(progress)
        db.session.flush()

    progress.score = max(progress.score, submission.score)
    if submission.status == 'checked':
        progress.status = 'completed'
        progress.completed_at = progress.completed_at or submission.submitted_at
        return

    progress.status = 'needs_revision'
    progress.completed_at = None


@teacher_bp.post('/classes/<int:classroom_id>/lessons')
@auth_required([UserRole.TEACHER])
def create_class_lesson(current_user: User, classroom_id: int):
    classroom = Classroom.query.filter_by(id=classroom_id, teacher_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    save_draft = _is_draft_save(data)
    missing_fields = [] if save_draft else _missing_lesson_fields(data)
    if missing_fields:
        labels = ', '.join(LESSON_REQUIRED_FIELD_LABELS[field] for field in missing_fields)
        return {
            'message': f'Заполните обязательные поля: {labels}.',
            'fields': missing_fields,
        }, 400

    title = str(data.get('title') or '').strip() or 'Черновик урока'
    summary = str(data.get('summary') or '').strip() or 'Черновик урока. Заполните описание перед публикацией.'

    age_group = _normalize_age_group(data.get('age_group'))
    module = _get_or_create_custom_module(classroom, age_group)
    previous_lesson = Lesson.query.filter_by(module_id=module.id).order_by(Lesson.order_index.desc()).first()
    order_index = (previous_lesson.order_index if previous_lesson else 0) + 1

    theory_text = str(data.get('theory_text') or '').strip()
    key_points = _split_lines(data.get('key_points')) or _split_csv(data.get('key_points'))
    theory_blocks = _build_teacher_theory_blocks(title, summary, theory_text, key_points)
    interactive_steps = _build_teacher_interactive_steps(data.get('interactive_steps'))

    lesson = Lesson(
        module_id=module.id,
        slug=f'teacher-class-{classroom.id}-lesson-{order_index}-{generate_code(4).lower()}',
        title=title,
        summary=summary,
        content_format=str(data.get('content_format') or 'mixed').strip() or 'mixed',
        theory_blocks=theory_blocks,
        interactive_steps=interactive_steps,
        order_index=order_index,
        duration_minutes=_safe_int(data.get('duration_minutes'), 10, minimum=5, maximum=180),
        passing_score=_safe_int(data.get('passing_score'), 70, minimum=0, maximum=100),
        is_published=False,
        created_by_id=current_user.id,
        authoring_metadata={},
    )
    db.session.add(lesson)
    db.session.flush()

    try:
        lesson.authoring_metadata = _authoring_metadata_for_write(lesson, data)
        if not save_draft:
            task = _build_teacher_task(lesson, data)
            if task is not None:
                db.session.add(task)
            quiz = build_lesson_quiz(lesson, data.get('quiz'), title, question_prefix='teacher-q')
            if quiz is not None:
                db.session.add(quiz)
            readiness_errors = lesson_publish_readiness_errors(lesson)
            if readiness_errors:
                db.session.rollback()
                return {
                    'message': 'Урок нельзя сохранить без обязательного содержания.',
                    'errors': readiness_errors,
                }, 400
    except ValueError as exc:
        db.session.rollback()
        return {'message': str(exc)}, 400

    db.session.commit()
    return {'lesson': lesson.to_authoring_dict(), 'catalog_item': _lesson_catalog_item(lesson)}, 201


@teacher_bp.get('/classes/<int:classroom_id>/lessons')
@auth_required([UserRole.TEACHER])
def list_class_lessons(current_user: User, classroom_id: int):
    classroom = Classroom.query.filter_by(id=classroom_id, teacher_id=current_user.id).first_or_404()
    status = _lesson_list_status_from_request()
    if status is None:
        return {
            'message': 'Некорректный статус урока.',
            'allowed_statuses': sorted(VALID_LESSON_LIST_STATUSES),
        }, 400

    page, page_size = pagination_params(request.args)
    query = _filter_lessons_by_status(
        Lesson.query.join(Module).filter(
            Module.slug.like(f'{custom_classroom_module_slug_prefix(classroom.id)}%')
        ),
        status,
    ).order_by(Lesson.updated_at.desc(), Lesson.id.desc())
    lessons, pagination = paginate_query(query, page=page, page_size=page_size)
    return {
        'lessons': [
            {
                **lesson.to_authoring_summary_dict(),
                'classroom_id': classroom.id,
                'classroom_name': classroom.name,
            }
            for lesson in lessons
        ],
        'pagination': pagination,
    }


@teacher_bp.get('/lessons/<int:lesson_id>')
@auth_required([UserRole.TEACHER])
def get_teacher_lesson(current_user: User, lesson_id: int):
    lesson = _teacher_lesson_or_404(current_user, lesson_id)
    return {'lesson': lesson.to_authoring_dict()}


@teacher_bp.patch('/lessons/<int:lesson_id>')
@auth_required([UserRole.TEACHER])
def update_teacher_lesson(current_user: User, lesson_id: int):
    lesson = _teacher_lesson_or_404(current_user, lesson_id)
    data = request.get_json() or {}
    conflict = _check_lesson_version(lesson, data)
    if conflict:
        return conflict
    if _is_draft_save(data) and lesson.is_published and lesson.archived_at is None:
        return {
            'message': 'Нельзя сохранять неполный черновик поверх опубликованного урока. Сначала снимите урок с публикации.'
        }, 409
    try:
        _apply_teacher_lesson_changes(lesson, data)
    except ValueError as exc:
        db.session.rollback()
        return {'message': str(exc)}, 400
    if lesson.is_published or _is_complete_builder_payload(data):
        readiness_errors = lesson_publish_readiness_errors(lesson)
        if readiness_errors:
            db.session.rollback()
            return {
                'message': 'Урок нельзя сохранить в таком состоянии.',
                'errors': readiness_errors,
            }, 400
    lesson.version += 1
    try:
        db.session.commit()
    except StaleDataError:
        return _stale_lesson_write_response(lesson_id)
    return {'lesson': lesson.to_authoring_dict()}


@teacher_bp.post('/lessons/<int:lesson_id>/clone')
@auth_required([UserRole.TEACHER])
def clone_teacher_lesson(current_user: User, lesson_id: int):
    source = db.get_or_404(Lesson, lesson_id)
    target_classroom_id = _parse_positive_int((request.get_json() or {}).get('classroom_id'))
    if target_classroom_id is None:
        return {'message': 'Укажите класс, в библиотеку которого нужно сохранить копию.'}, 400
    classroom = Classroom.query.filter_by(id=target_classroom_id, teacher_id=current_user.id).first_or_404()
    is_public_source = (
        not source.module.is_custom_classroom_module
        and source.module.is_published
        and source.is_published
        and source.archived_at is None
    )
    if not is_public_source and not _teacher_owns_lesson(current_user, source):
        return {'message': 'Нельзя копировать недоступный урок.'}, 403
    module = _get_or_create_custom_module(classroom, source.module.age_group)
    previous = Lesson.query.filter_by(module_id=module.id).order_by(Lesson.order_index.desc()).first()
    clone = Lesson(
        module_id=module.id,
        slug=f'teacher-class-{classroom.id}-lesson-{(previous.order_index if previous else 0) + 1}-{generate_code(4).lower()}',
        title=f'Копия: {source.title}',
        summary=source.summary,
        order_index=(previous.order_index if previous else 0) + 1,
        is_published=False,
        created_by_id=current_user.id,
    )
    clone_lesson_content(source, clone)
    db.session.add(clone)
    db.session.commit()
    return {'lesson': clone.to_authoring_dict(), 'catalog_item': _lesson_catalog_item(clone)}, 201


@teacher_bp.post('/lessons/<int:lesson_id>/share')
@auth_required([UserRole.TEACHER])
def share_teacher_lesson(current_user: User, lesson_id: int):
    lesson = _teacher_lesson_or_404(current_user, lesson_id)
    data = request.get_json(silent=True) or {}
    conflict = _check_optional_lesson_version(lesson, data)
    if conflict:
        return conflict
    classroom_id = _parse_positive_int(data.get('classroom_id'))
    source_classroom_id = lesson.module.custom_classroom_id
    if classroom_id is not None and classroom_id != source_classroom_id:
        return {'message': 'Чтобы поделиться с другим классом, сначала создайте копию урока в его библиотеке.'}, 400
    classroom = Classroom.query.filter_by(id=source_classroom_id, teacher_id=current_user.id).first_or_404()
    readiness_errors = lesson_publish_readiness_errors(lesson)
    if readiness_errors:
        return {
            'message': 'Урок пока нельзя открыть классу.',
            'errors': readiness_errors,
        }, 400
    if lesson.is_published and lesson.archived_at is None:
        return {'lesson': lesson.to_authoring_dict()}
    lesson.is_published = True
    lesson.archived_at = None
    lesson.published_at = lesson.published_at or datetime.now(UTC)
    lesson.version += 1
    # Persist visibility before notifications/emails can be sent.
    try:
        db.session.commit()
    except StaleDataError:
        return _stale_lesson_write_response(lesson_id)
    notifications.notify_students_new_class_lesson(current_user, classroom, lesson)
    db.session.commit()
    return {'lesson': lesson.to_authoring_dict()}


@teacher_bp.post('/classes/<int:classroom_id>/assignments')
@auth_required([UserRole.TEACHER])
def create_assignment(current_user: User, classroom_id: int):
    classroom = Classroom.query.filter_by(id=classroom_id, teacher_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    missing_fields = _missing_assignment_fields(data)
    if missing_fields:
        labels = ', '.join(ASSIGNMENT_REQUIRED_FIELD_LABELS[field] for field in missing_fields)
        return {
            'message': f'Заполните обязательные поля: {labels}.',
            'fields': missing_fields,
        }, 400

    lesson_id = data.get('lesson_id')
    lesson = None
    assignment_type = normalize_assignment_type(data.get('assignment_type'))
    submission_format = normalize_submission_format(data.get('submission_format'))
    parsed_lesson_id = _parse_positive_int(lesson_id)
    if parsed_lesson_id is None:
        return {'message': 'Некорректный идентификатор урока.'}, 400
    lesson = db.get_or_404(Lesson, parsed_lesson_id)
    if not _teacher_can_use_lesson(classroom, lesson):
        return {'message': 'Этот урок нельзя назначить выбранному классу.'}, 403
    title = (data.get('title') or '').strip()
    description = _compose_assignment_description(data, assignment_type)

    assignment = Assignment(
        classroom_id=classroom.id,
        lesson_id=lesson.id,
        title=title,
        description=encode_assignment_description(description, assignment_type, submission_format),
        difficulty=_normalize_difficulty(data.get('difficulty')),
        due_date=_normalize_due_date(data.get('due_date')),
        xp_reward=0,
    )
    db.session.add(assignment)
    db.session.flush()
    # The assignment must be durable before an email or in-app notification
    # can link a student to it.
    db.session.commit()
    notifications.notify_students_new_assignment(current_user, classroom, assignment)
    db.session.commit()
    return {'assignment': assignment.to_dict()}, 201


@teacher_bp.get('/classes/<int:classroom_id>/assignments')
@auth_required([UserRole.TEACHER])
def list_assignments(current_user: User, classroom_id: int):
    page, page_size = pagination_params(request.args)
    return TeacherQueryService().class_assignments_payload(
        current_user,
        classroom_id,
        page=page,
        page_size=page_size,
    )


@teacher_bp.get('/assignments/<int:assignment_id>/submissions')
@auth_required([UserRole.TEACHER])
def assignment_submissions(current_user: User, assignment_id: int):
    status = (request.args.get('status') or 'all').strip().lower()
    if status not in VALID_SUBMISSION_LIST_STATUSES:
        return {
            'message': 'Некорректный статус работы.',
            'allowed_statuses': sorted(VALID_SUBMISSION_LIST_STATUSES),
        }, 400
    page, page_size = pagination_params(request.args)
    try:
        return TeacherQueryService().assignment_submissions_payload(
            current_user,
            assignment_id,
            page=page,
            page_size=page_size,
            status=status,
        )
    except PermissionError:
        return {'message': 'Forbidden'}, 403


@teacher_bp.patch('/submissions/<int:submission_id>/grade')
@auth_required([UserRole.TEACHER])
def grade_submission(current_user: User, submission_id: int):
    submission = db.get_or_404(AssignmentSubmission, submission_id)
    if submission.assignment.classroom.teacher_id != current_user.id:
        return {'message': 'Forbidden'}, 403
    data = request.get_json() or {}
    submission.score = _safe_int(data.get('score', submission.score), submission.score, minimum=0, maximum=100)
    submission.feedback = data.get('feedback', submission.feedback)
    submission.status = _normalize_submission_review_status(data.get('status'))
    _sync_lesson_progress_from_review(submission)
    db.session.commit()
    return {'submission': submission.to_dict()}


@teacher_bp.get('/lesson-catalog')
@auth_required([UserRole.TEACHER])
def lesson_catalog(current_user: User):
    classroom_id = request.args.get('classroom_id', type=int)
    classroom = None
    if classroom_id:
        classroom = Classroom.query.filter_by(id=classroom_id, teacher_id=current_user.id).first_or_404()
    source = (request.args.get('source') or 'all').strip().lower()
    if source not in VALID_CATALOG_SOURCES:
        return {
            'message': 'Некорректный источник уроков.',
            'allowed_sources': sorted(VALID_CATALOG_SOURCES),
        }, 400
    search = (request.args.get('q') or '').strip()
    page, page_size = pagination_params(request.args)
    query = _catalog_lessons_for_teacher(
        current_user,
        classroom,
        source=source,
        search=search,
    )
    lessons, pagination = paginate_query(query, page=page, page_size=page_size)
    return {
        'lessons': [_lesson_catalog_item(lesson) for lesson in lessons],
        'pagination': pagination,
        'filters': {'source': source, 'q': search},
    }


@teacher_bp.get('/parent-threads')
@auth_required([UserRole.TEACHER])
def teacher_parent_threads(current_user: User):
    return parent_messaging.summary_for_teacher(current_user)


@teacher_bp.get('/parent-threads/<int:thread_id>/messages')
@auth_required([UserRole.TEACHER])
def teacher_parent_thread_messages(current_user: User, thread_id: int):
    return parent_messaging.list_messages_teacher(current_user, thread_id)


@teacher_bp.post('/parent-threads/<int:thread_id>/messages')
@auth_required([UserRole.TEACHER])
def teacher_parent_thread_send(current_user: User, thread_id: int):
    return parent_messaging.send_message_teacher(current_user, thread_id)


@teacher_bp.post('/parent-threads/<int:thread_id>/read')
@auth_required([UserRole.TEACHER])
def teacher_parent_thread_read(current_user: User, thread_id: int):
    return parent_messaging.mark_read_teacher(current_user, thread_id)
