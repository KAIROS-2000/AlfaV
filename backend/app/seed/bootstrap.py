from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime

from flask import current_app
from sqlalchemy import inspect, text

from ..core.db import db
from ..core.security import hash_password
from ..models.learning import (
    Achievement,
    Assignment,
    ClassMembership,
    Classroom,
    Lesson,
    Module,
    Quiz,
    Task,
    age_group_supports_code,
    has_explicit_code_task_intent,
    normalize_task_validation,
)
from ..models.useful import UsefulTask
from ..models.user import User, UserRole


def generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def bootstrap_superadmin() -> None:
    email = current_app.config['SUPERADMIN_EMAIL'].strip().lower()
    password = current_app.config.get('SUPERADMIN_PASSWORD') or ''
    if not email or not password:
        return
    if User.query.filter_by(email=email).first():
        return
    db.session.add(
        User(
            full_name=current_app.config['SUPERADMIN_NAME'],
            email=email,
            password_hash=hash_password(password),
            role=UserRole.SUPERADMIN,
            age_group='adult',
            xp=5000,
            email_verified=True,
            email_verified_at=datetime.now(UTC),
        )
    )
    db.session.commit()


def seed_achievements() -> None:
    existing_codes = {achievement.code for achievement in Achievement.query.all()}
    achievements = [
        ('first_code', 'Первый код', 'Написать первую программу', 'start', 'sparkles', 50),
        ('perfect_five', 'Безошибочный', 'Пройти 5 уроков подряд без ошибок', 'mastery', 'badge-check', 150),
        ('marathon', 'Марафонец', 'Заходить 30 дней подряд', 'persistence', 'flame', 500),
        ('explorer', 'Исследователь', 'Закрыть все модули возрастной группы', 'progress', 'map', 300),
        ('lightning', 'Молния', 'Решить задачу меньше чем за минуту', 'speed', 'zap', 75),
        ('patience', 'Терпение', 'Решить задачу, потратив больше 10 минут, но без ошибок', 'persistence', 'clock', 200),
        ('night_owl', 'Вечерний программист', 'Пройти урок после 23:00', 'time', 'moon', 50),
        ('early_bird', 'Утренний старт', 'Пройти урок до 8:00', 'time', 'sunrise', 50),
        ('golden_streak', 'Золотая серия', 'Пройти 10 уроков подряд без перерыва более 5 минут', 'persistence', 'trophy', 300),
        ('sprinter', 'Спринтер', 'Пройти 5 уроков за 20 минут', 'speed', 'timer', 175),
        ('no_hints', 'Без подсказок', 'Решить задачу, не используя встроенные подсказки', 'mastery', 'eye-off', 125),
        ('revisitor', 'Повторитель', 'Вернуться к старому уроку и пройти его идеально', 'persistence', 'rotate-ccw', 80),
    ]
    added = False
    for code, name, description, category, icon, xp in achievements:
        if code not in existing_codes:
            db.session.add(Achievement(code=code, name=name, description=description, category=category, icon=icon, xp_reward=xp))
            added = True
    if added:
        db.session.commit()


def cleanup_deprecated_learning_artifacts() -> None:
    changed = False

    mentor_achievement = Achievement.query.filter_by(code='mentor').first()
    if mentor_achievement:
        db.session.delete(mentor_achievement)
        db.session.flush()
        changed = True

    users_table = User.__table__.name
    existing_columns = {column['name'] for column in inspect(db.engine).get_columns(users_table)}
    for fragments in (('ava', 'tar'), ('compan', 'ion')):
        legacy_column = ''.join(fragments)
        if legacy_column in existing_columns:
            db.session.execute(text(f'ALTER TABLE {users_table} DROP COLUMN {legacy_column}'))
            changed = True

    legacy_discussion_table = ''.join(['fo', 'rum', '_posts'])
    if inspect(db.engine).has_table(legacy_discussion_table):
        db.session.execute(text(f'DROP TABLE {legacy_discussion_table}'))
        changed = True

    if changed:
        db.session.commit()


def _question_single(qid: str, prompt: str, options: list[str], correct: int) -> dict:
    return {'id': qid, 'type': 'single', 'prompt': prompt, 'options': options, 'correct': [correct]}


def _question_multiple(qid: str, prompt: str, options: list[str], correct: list[int]) -> dict:
    return {'id': qid, 'type': 'multiple', 'prompt': prompt, 'options': options, 'correct': correct}


def _question_order(qid: str, prompt: str, items: list[str], correct: list[str]) -> dict:
    return {'id': qid, 'type': 'order', 'prompt': prompt, 'items': items, 'correct': correct}


def _question_match(qid: str, prompt: str, left: list[str], right: list[str], correct: dict[str, str]) -> dict:
    return {'id': qid, 'type': 'match', 'prompt': prompt, 'left': left, 'right': right, 'correct': correct}


def _lesson_payload(
    title: str,
    summary: str,
    concepts: list[str],
    practice_title: str,
    practice_prompt: str,
    answer_keywords: list[str],
    task_hints: list[str],
    quiz_questions: list[dict],
    starter_code: str = '',
    task_validation: dict | None = None,
) -> dict:
    if has_explicit_code_task_intent(
        title=practice_title,
        prompt=practice_prompt,
        starter_code=starter_code,
    ) and not starter_code:
        raise ValueError(f'Code lesson "{title}" requires starter_code and stdin/stdout tests.')
    if starter_code:
        if not isinstance(task_validation, dict):
            raise ValueError(f'Code lesson "{title}" requires explicit stdin/stdout tests in task_validation.')
        raw_tests = task_validation.get('tests')
        if not isinstance(raw_tests, list) or not raw_tests:
            raise ValueError(f'Code lesson "{title}" requires at least one stdin/stdout test in task_validation.')
    return {
        'title': title,
        'summary': summary,
        'theory_blocks': [
            {'type': 'hero', 'title': title, 'text': summary},
            {'type': 'list', 'title': 'Ключевые понятия', 'items': concepts},
            {'type': 'tip', 'title': 'Совет наставника', 'text': 'Сначала прочитай объяснение, потом измени пример и только после этого переходи к практике.'},
        ],
        'interactive_steps': [
            {'title': 'Пошаговый пример', 'text': 'Нажимай Далее и смотри, как меняется результат после каждого шага.'},
            {'title': 'Мини-эксперимент', 'text': 'Попробуй изменить одну команду или значение и посмотри, что изменится.'},
        ],
        'task': {
            'title': practice_title,
            'prompt': practice_prompt,
            'starter_code': starter_code,
            'validation': task_validation or {'keywords': answer_keywords},
            'hints': task_hints,
        },
        'quiz': quiz_questions,
    }


def _stdio_validation(language: str, tests: list[dict], time_limit_ms: int = 2000, memory_limit_mb: int = 128) -> dict:
    return {
        'evaluation_mode': 'stdin_stdout',
        'language': language,
        'tests': tests,
        'time_limit_ms': time_limit_ms,
        'memory_limit_mb': memory_limit_mb,
    }


def _legacy_seeded_code_task_updates() -> dict[tuple[str, str], dict]:
    return {
        ('middle-python-intro', 'Выведи сообщение'): {
            'starter_code': 'print("Я изучаю Python")\n',
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': '', 'expected': 'Я изучаю Python\n'},
                ],
            ),
        },
        ('middle-python-intro', 'Создай переменные'): {
            'starter_code': 'name = "Аня"\nage = 12\nprint(name, age)\n',
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': '', 'expected': 'Аня 12\n'},
                ],
            ),
        },
        ('middle-python-intro', 'Поздоровайся по имени'): {
            'starter_code': 'name = input().strip()\nprint(f"Привет, {name}")\n',
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': 'Аня\n', 'expected': 'Привет, Аня\n'},
                    {'label': 'Тест 2', 'input': 'Тимур\n', 'expected': 'Привет, Тимур\n'},
                ],
            ),
        },
        ('middle-conditions', 'Проверь возраст'): {
            'starter_code': 'age = int(input())\nif age >= 12:\n    print("Средняя группа")\nelse:\n    print("Младшая группа")\n',
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': '12\n', 'expected': 'Средняя группа\n'},
                    {'label': 'Тест 2', 'input': '9\n', 'expected': 'Младшая группа\n'},
                ],
            ),
        },
        ('middle-conditions', 'Проверь пропуск'): {
            'prompt': 'Считай has_ticket и is_on_time из stdin. Выведи pass, если оба равны 1, иначе wait.',
            'hints': [
                'Сначала получи два числа через input(): has_ticket и is_on_time.',
                'Объедини обе проверки в одном условии через and.',
                'Если оба значения равны 1, выведи pass, иначе выведи wait.',
            ],
            'starter_code': (
                'has_ticket = int(input())\n'
                'is_on_time = int(input())\n'
                '\n'
                'if has_ticket == 1 and is_on_time == 1:\n'
                '    print("pass")\n'
                'else:\n'
                '    print("wait")\n'
            ),
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': '1\n1\n', 'expected': 'pass\n'},
                    {'label': 'Тест 2', 'input': '1\n0\n', 'expected': 'wait\n'},
                    {'label': 'Тест 3', 'input': '0\n1\n', 'expected': 'wait\n'},
                ],
            ),
        },
        ('middle-conditions', 'Определи категорию'): {
            'prompt': 'Считай возраст из stdin и выведи junior, middle или senior.',
            'hints': [
                'Сначала получи возраст через input() и преврати его в число.',
                'Используй if / elif / else, чтобы разделить три возрастные категории.',
                'Для младшей группы выведи junior, для средней middle, для старшей senior.',
            ],
            'starter_code': (
                'age = int(input())\n'
                '\n'
                'if age < 12:\n'
                '    print("junior")\n'
                'elif age < 15:\n'
                '    print("middle")\n'
                'else:\n'
                '    print("senior")\n'
            ),
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': '10\n', 'expected': 'junior\n'},
                    {'label': 'Тест 2', 'input': '13\n', 'expected': 'middle\n'},
                    {'label': 'Тест 3', 'input': '16\n', 'expected': 'senior\n'},
                ],
            ),
        },
        ('middle-functions', 'Создай greet'): {
            'prompt': 'Считай имя из stdin, создай функцию greet(name) и выведи приветствие.',
            'hints': [
                'Сначала получи имя пользователя через input().',
                'Объяви функцию greet(name), которая печатает приветствие.',
                'После объявления функции вызови её с именем из ввода.',
            ],
            'starter_code': 'name = input().strip()\n\ndef greet(name):\n    print(f"Привет, {name}")\n\ngreet(name)\n',
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': 'Маша\n', 'expected': 'Привет, Маша\n'},
                    {'label': 'Тест 2', 'input': 'Илья\n', 'expected': 'Привет, Илья\n'},
                ],
            ),
        },
        ('middle-functions', 'Посчитай сумму'): {
            'prompt': 'Считай два числа из stdin, создай функцию add(a, b) и выведи сумму.',
            'hints': [
                'Сначала получи два числа через input() и сохрани их в переменные.',
                'Создай функцию add(a, b), которая возвращает сумму через return.',
                'В конце выведи результат вызова add(a, b) через print().',
            ],
            'starter_code': (
                'a = int(input())\n'
                'b = int(input())\n'
                '\n'
                'def add(a, b):\n'
                '    return a + b\n'
                '\n'
                'print(add(a, b))\n'
            ),
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': '2\n3\n', 'expected': '5\n'},
                    {'label': 'Тест 2', 'input': '-1\n10\n', 'expected': '9\n'},
                ],
            ),
        },
        ('middle-functions', 'Мини-проект заметки'): {
            'prompt': 'Считай заголовок и текст из stdin, собери заметку с помощью 2 функций и выведи её.',
            'hints': [
                'Сначала получи заголовок и текст заметки через input().',
                'Сделай одну функцию для сборки строки заметки, а вторую для вывода результата.',
                'В конце вызови функции по очереди и выведи готовую заметку.',
            ],
            'starter_code': (
                'title = input().strip()\n'
                'text = input().strip()\n'
                '\n'
                'def build_note(title, text):\n'
                '    return f"{title}: {text}"\n'
                '\n'
                'def show_note(note):\n'
                '    print(note)\n'
                '\n'
                'show_note(build_note(title, text))\n'
            ),
            'validation': _stdio_validation(
                'python',
                [
                    {'label': 'Тест 1', 'input': 'План\nСделать проект\n', 'expected': 'План: Сделать проект\n'},
                    {'label': 'Тест 2', 'input': 'Идея\nПриложение для заметок\n', 'expected': 'Идея: Приложение для заметок\n'},
                ],
            ),
        },
        ('senior-js-basics', 'Создай переменную score'): {
            'starter_code': 'let score = 10;\nconsole.log(score);\n',
            'validation': _stdio_validation(
                'javascript',
                [
                    {'label': 'Тест 1', 'input': '', 'expected': '10\n'},
                ],
            ),
        },
        ('senior-js-basics', 'Проверь балл'): {
            'prompt': 'Создай функцию checkScore(score). Выведи результаты для 72 и 40: pass или retry.',
            'hints': [
                'Опиши функцию checkScore(score), которая возвращает строку, а не печатает её внутри себя.',
                'Если балл не меньше 70, функция должна вернуть pass, иначе retry.',
                'После этого выведи через console.log результат для 72 и для 40.',
            ],
            'starter_code': (
                'function checkScore(score) {\n'
                '  if (score >= 70) {\n'
                '    return "pass";\n'
                '  }\n'
                '  return "retry";\n'
                '}\n'
                '\n'
                'console.log(checkScore(72));\n'
                'console.log(checkScore(40));\n'
            ),
            'validation': _stdio_validation(
                'javascript',
                [
                    {'label': 'Тест 1', 'input': '', 'expected': 'pass\nretry\n'},
                ],
            ),
        },
        ('senior-js-basics', 'Сделай кнопку'): {
            'prompt': 'У объекта button уже есть addEventListener и click(). Добавь обработчик click, который меняет label на "Готово", затем выведи результат.',
            'hints': [
                'Используй button.addEventListener("click", ...), чтобы зарегистрировать обработчик.',
                'Внутри обработчика поменяй button.label на "Готово".',
                'После регистрации вызови button.click() и выведи button.label через console.log().',
            ],
            'starter_code': (
                'const button = {\n'
                '  label: "Нажми",\n'
                '  handlers: {},\n'
                '  addEventListener(event, handler) {\n'
                '    this.handlers[event] = handler;\n'
                '  },\n'
                '  click() {\n'
                '    if (this.handlers.click) {\n'
                '      this.handlers.click();\n'
                '    }\n'
                '  },\n'
                '};\n'
                '\n'
                'button.addEventListener("click", () => {\n'
                '  button.label = "Готово";\n'
                '});\n'
                '\n'
                'button.click();\n'
                'console.log(button.label);\n'
            ),
            'validation': _stdio_validation(
                'javascript',
                [
                    {'label': 'Тест 1', 'input': '', 'expected': 'Готово\n'},
                ],
            ),
        },
    }


def seed_modules() -> None:
    if Module.query.count() > 0:
        return

    from .learning_content import build_learning_modules

    modules_data = build_learning_modules(
        _lesson_payload,
        _question_single,
        _question_multiple,
        _question_order,
        _question_match,
        _stdio_validation,
    )

    for group_index, module_data in enumerate(modules_data, start=1):
        module = Module(
            slug=module_data['slug'],
            title=module_data['title'],
            description=module_data['description'],
            age_group=module_data['age_group'],
            icon=module_data['icon'],
            color=module_data['color'],
            order_index=group_index,
            is_published=True,
        )
        db.session.add(module)
        db.session.flush()
        for lesson_index, lesson_payload in enumerate(module_data['lessons'], start=1):
            raw_task = lesson_payload['task']
            task_type = 'code' if age_group_supports_code(module.age_group) and raw_task.get('starter_code') else 'text'
            starter_code = raw_task.get('starter_code', '') if task_type == 'code' else ''
            if (
                has_explicit_code_task_intent(
                    title=raw_task.get('title'),
                    prompt=raw_task.get('prompt'),
                    starter_code=raw_task.get('starter_code', ''),
                )
                and task_type != 'code'
            ):
                raise ValueError(
                    f'Seed lesson "{module.slug}/{lesson_payload["title"]}" has code intent but configured as text task.'
                )
            task_validation = normalize_task_validation(
                raw_task['validation'],
                task_type=task_type,
                age_group=module.age_group,
            )
            lesson = Lesson(
                module_id=module.id,
                slug=f"{module.slug}-lesson-{lesson_index}",
                title=lesson_payload['title'],
                summary=lesson_payload['summary'],
                theory_blocks=lesson_payload['theory_blocks'],
                interactive_steps=lesson_payload['interactive_steps'],
                order_index=lesson_index,
                duration_minutes=8 + lesson_index * 2,
                passing_score=70,
                content_format='mixed',
            )
            db.session.add(lesson)
            db.session.flush()
            db.session.add(
                Task(
                    lesson_id=lesson.id,
                    task_type=task_type,
                    title=raw_task['title'],
                    prompt=raw_task['prompt'],
                    starter_code=starter_code,
                    validation=task_validation,
                    hints=raw_task['hints'],
                    xp_reward=30,
                )
            )
            db.session.add(
                Quiz(
                    lesson_id=lesson.id,
                    title=f"Мини-тест: {lesson.title}",
                    passing_score=70,
                    questions=lesson_payload['quiz'],
                    xp_reward=50,
                )
            )
    db.session.commit()


def seed_demo_users() -> None:
    student_email = (current_app.config.get('DEMO_STUDENT_EMAIL') or '').strip().lower()
    student_password = current_app.config.get('DEMO_STUDENT_PASSWORD') or ''
    teacher_email = (current_app.config.get('DEMO_TEACHER_EMAIL') or '').strip().lower()
    teacher_password = current_app.config.get('DEMO_TEACHER_PASSWORD') or ''
    admin_email = (current_app.config.get('DEMO_ADMIN_EMAIL') or '').strip().lower()
    admin_password = current_app.config.get('DEMO_ADMIN_PASSWORD') or ''

    if not all([student_email, student_password, teacher_email, teacher_password, admin_email, admin_password]):
        return

    if User.query.filter(
        (User.email == student_email) | (User.email == teacher_email) | (User.email == admin_email)
    ).first():
        return

    verified_at = datetime.now(UTC)
    users = [
        User(
            full_name='Тестовый ученик',
            email=student_email,
            password_hash=hash_password(student_password),
            role=UserRole.STUDENT,
            age_group='middle',
            xp=360,
            streak=6,
            email_verified=True,
            email_verified_at=verified_at,
        ),
        User(
            full_name='Тестовый учитель',
            email=teacher_email,
            password_hash=hash_password(teacher_password),
            role=UserRole.TEACHER,
            age_group='adult',
            xp=1200,
            streak=12,
            email_verified=True,
            email_verified_at=verified_at,
        ),
        User(
            full_name='Тестовый администратор',
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=UserRole.ADMIN,
            age_group='adult',
            xp=2400,
            streak=18,
            email_verified=True,
            email_verified_at=verified_at,
        ),
    ]
    db.session.add_all(users)
    db.session.commit()


def seed_classes_and_assignments() -> None:
    if Classroom.query.count() > 0:
        return
    teacher_email = (current_app.config.get('DEMO_TEACHER_EMAIL') or '').strip().lower()
    student_email = (current_app.config.get('DEMO_STUDENT_EMAIL') or '').strip().lower()
    if not teacher_email or not student_email:
        return

    teacher = User.query.filter_by(email=teacher_email).first()
    student = User.query.filter_by(email=student_email).first()
    lesson = Lesson.query.join(Module).filter(Module.slug == 'middle-python-intro').order_by(Lesson.order_index.asc()).first()
    if not all([teacher, student, lesson]):
        return

    classroom_code = ((current_app.config.get('DEMO_CLASS_CODE') or '').strip().upper() or generate_code(6))
    classroom = Classroom(name='Тестовый класс', description='Класс для проверки teacher-панели', code=classroom_code, teacher_id=teacher.id)
    db.session.add(classroom)
    db.session.flush()
    db.session.add(ClassMembership(classroom_id=classroom.id, student_id=student.id))
    db.session.add(
        Assignment(
            classroom_id=classroom.id,
            lesson_id=lesson.id,
            title='Домашнее задание: приветствие по имени',
            description='Напиши короткую программу, которая спрашивает имя и приветствует пользователя.',
            difficulty='easy',
            due_date=None,
            xp_reward=90,
        )
    )
    db.session.commit()


def repair_legacy_code_task_validations() -> None:
    updates = _legacy_seeded_code_task_updates()
    changed = False
    for task in Task.query.join(Lesson).join(Module).all():
        if not age_group_supports_code(task.lesson.module.age_group):
            target_validation = normalize_task_validation(
                task.validation,
                is_custom_lesson=task.lesson.module.is_custom_classroom_module,
                task_type='text',
                age_group=task.lesson.module.age_group,
            )
            if task.task_type != 'text':
                task.task_type = 'text'
                changed = True
            if task.starter_code:
                task.starter_code = ''
                changed = True
            if task.validation != target_validation:
                task.validation = target_validation
                changed = True
            continue

        key = (task.lesson.module.slug, task.title)
        update = updates.get(key)
        if update:
            target_starter_code = update['starter_code']
            target_validation = normalize_task_validation(
                update['validation'],
                is_custom_lesson=task.lesson.module.is_custom_classroom_module,
                task_type='code',
                age_group=task.lesson.module.age_group,
            )
            target_prompt = update.get('prompt')
            target_hints = update.get('hints')
            if task.task_type != 'code':
                task.task_type = 'code'
                changed = True
            if target_prompt is not None and task.prompt != target_prompt:
                task.prompt = target_prompt
                changed = True
            if target_hints is not None and task.hints != target_hints:
                task.hints = target_hints
                changed = True
            if task.starter_code != target_starter_code:
                task.starter_code = target_starter_code
                changed = True
            if task.validation != target_validation:
                task.validation = target_validation
                changed = True
            continue

        if task.task_type != 'code':
            continue

        normalized = normalize_task_validation(
            task.validation,
            is_custom_lesson=task.lesson.module.is_custom_classroom_module,
            task_type=task.task_type,
            age_group=task.lesson.module.age_group,
        )

        # Code tasks always use the real stdin/stdout judge.
        if task.validation != normalized:
            task.validation = normalized
            changed = True

    if changed:
        db.session.commit()


def seed_useful_tasks() -> None:
    """Seed 3 published useful tasks per age group (9 total). Idempotent by slug."""
    tasks = [
        # ── Junior (10–12 лет) ─────────────────────────────────────────────
        {
            'slug': 'junior-scratch-platformer',
            'title': 'Сделай платформер в Scratch',
            'summary': (
                'Создай персонажа, который прыгает по платформам и собирает монеты. '
                'Scratch не требует написания кода — всё строится из блоков, как конструктор. '
                'Отличный старт для тех, кто ещё не писал программы.'
            ),
            'body': (
                '## Что нужно сделать\n'
                '1. Зарегистрируйся на scratch.mit.edu\n'
                '2. Создай нового персонажа и нарисуй платформы\n'
                '3. Добавь блок «когда клавиша ↑ нажата → изменить y на 10»\n'
                '4. Добавь гравитацию: в цикле уменьшай y на 1, пока не касаешься пола\n'
                '5. Добавь монеты — спрайты, которые исчезают при прикосновении\n\n'
                '## Совет\n'
                'Посмотри раздел «Примеры» на сайте Scratch — там есть готовые платформеры '
                'с открытым кодом. Разберись, как они работают, и улучши свой.'
            ),
            'external_url': 'https://scratch.mit.edu/projects/editor/?tutorial=all',
            'age_groups': ['junior'],
            'topic': 'игры',
            'difficulty': 'easy',
            'is_published': True,
        },
        {
            'slug': 'junior-html-my-page',
            'title': 'Моя первая страница на HTML',
            'summary': (
                'Напиши HTML-страницу о себе: имя, любимые игры, раздел «мои интересы». '
                'Узнаешь, что такое теги, атрибуты и как браузер читает код.'
            ),
            'body': (
                '## Минимальная структура\n'
                '```html\n'
                '<!DOCTYPE html>\n'
                '<html>\n'
                '  <head><title>Моя страница</title></head>\n'
                '  <body>\n'
                '    <h1>Привет, я — Имя!</h1>\n'
                '    <p>Мне нравится программировать.</p>\n'
                '  </body>\n'
                '</html>\n'
                '```\n\n'
                '## Задание\n'
                '- Добавь заголовок h1 со своим именем\n'
                '- Добавь список ul/li с тремя любимыми играми или хобби\n'
                '- Добавь картинку через тег img\n'
                '- Открой файл в браузере и посмотри результат'
            ),
            'external_url': 'https://htmlacademy.ru/courses/basic-html-css',
            'age_groups': ['junior'],
            'topic': 'html',
            'difficulty': 'easy',
            'is_published': True,
        },
        {
            'slug': 'junior-python-turtle',
            'title': 'Рисуем геометрию с Python Turtle',
            'summary': (
                'С помощью модуля turtle нарисуй квадрат, треугольник и звезду. '
                'Узнаешь про циклы for и команды вперёд/поворот — первый настоящий Python.'
            ),
            'body': (
                '## Запуск\n'
                'Установи Python 3 и запусти IDLE или любой редактор.\n\n'
                '```python\n'
                'import turtle\n'
                't = turtle.Turtle()\n'
                'for _ in range(4):\n'
                '    t.forward(100)\n'
                '    t.right(90)\n'
                'turtle.done()\n'
                '```\n\n'
                '## Задания\n'
                '1. Квадрат (4 стороны, поворот 90°)\n'
                '2. Треугольник (3 стороны, поворот 120°)\n'
                '3. Звезда (5 лучей, поворот 144°)\n'
                '4. Попробуй изменить цвет через t.color("red")'
            ),
            'external_url': 'https://docs.python.org/3/library/turtle.html',
            'age_groups': ['junior'],
            'topic': 'python',
            'difficulty': 'easy',
            'is_published': True,
        },

        # ── Middle (13–15 лет) ─────────────────────────────────────────────
        {
            'slug': 'middle-python-guess-game',
            'title': 'Игра «Угадай число» на Python',
            'summary': (
                'Напиши игру: компьютер загадывает число от 1 до 100, игрок пытается угадать. '
                'Практика циклов while, условий if/elif/else, функции random.randint и ввода с клавиатуры.'
            ),
            'body': (
                '## Шаги\n'
                '```python\n'
                'import random\n\n'
                'secret = random.randint(1, 100)\n'
                'attempts = 0\n\n'
                'while True:\n'
                '    guess = int(input("Твой вариант: "))\n'
                '    attempts += 1\n'
                '    if guess < secret:\n'
                '        print("Больше!")\n'
                '    elif guess > secret:\n'
                '        print("Меньше!")\n'
                '    else:\n'
                '        print(f"Верно! Попыток: {attempts}")\n'
                '        break\n'
                '```\n\n'
                '## Усложнения\n'
                '- Добавь лимит попыток (например, 7)\n'
                '- Покажи рейтинг: «Отлично / Хорошо / Неплохо» в зависимости от числа попыток\n'
                '- Добавь возможность сыграть снова без перезапуска программы'
            ),
            'external_url': 'https://replit.com/languages/python3',
            'age_groups': ['middle'],
            'topic': 'python',
            'difficulty': 'easy',
            'is_published': True,
        },
        {
            'slug': 'middle-css-flexbox-card',
            'title': 'Карточка профиля на CSS Flexbox',
            'summary': (
                'Свёрстай карточку пользователя: аватар, имя, описание и кнопки «Написать» / «Подписаться». '
                'Знакомство с Flexbox, box-shadow, border-radius и hover-эффектами.'
            ),
            'body': (
                '## Что должно получиться\n'
                'Карточка 320px шириной: аватар сверху по центру, ниже имя жирным, '
                'затем короткое описание, затем два button в ряд через flex.\n\n'
                '## Ключевые свойства\n'
                '```css\n'
                '.card {\n'
                '  display: flex;\n'
                '  flex-direction: column;\n'
                '  align-items: center;\n'
                '  gap: 12px;\n'
                '  padding: 24px;\n'
                '  border-radius: 16px;\n'
                '  box-shadow: 0 4px 20px rgba(0,0,0,.08);\n'
                '}\n'
                '.actions { display: flex; gap: 8px; }\n'
                '```\n\n'
                '## Задание\n'
                '- Добавь transition на кнопки: плавное изменение фона при наведении\n'
                '- Сделай карточку адаптивной: на узком экране кнопки переносятся вертикально\n'
                '- Попробуй тёмную тему через media prefers-color-scheme'
            ),
            'external_url': 'https://flexboxfroggy.com/#ru',
            'age_groups': ['middle'],
            'topic': 'css',
            'difficulty': 'medium',
            'is_published': True,
        },
        {
            'slug': 'middle-algorithms-sorting',
            'title': 'Пузырьковая и быстрая сортировка',
            'summary': (
                'Реализуй два алгоритма сортировки на Python, сравни их скорость на 10 000 элементов. '
                'Поймёшь, что такое O(n²) vs O(n log n) на практике.'
            ),
            'body': (
                '## Пузырьковая сортировка\n'
                '```python\n'
                'def bubble_sort(arr):\n'
                '    n = len(arr)\n'
                '    for i in range(n):\n'
                '        for j in range(0, n - i - 1):\n'
                '            if arr[j] > arr[j + 1]:\n'
                '                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n'
                '    return arr\n'
                '```\n\n'
                '## Быстрая сортировка\n'
                '```python\n'
                'def quick_sort(arr):\n'
                '    if len(arr) <= 1:\n'
                '        return arr\n'
                '    pivot = arr[len(arr) // 2]\n'
                '    left = [x for x in arr if x < pivot]\n'
                '    mid  = [x for x in arr if x == pivot]\n'
                '    right= [x for x in arr if x > pivot]\n'
                '    return quick_sort(left) + mid + quick_sort(right)\n'
                '```\n\n'
                '## Сравни время\n'
                '```python\n'
                'import random, time\n'
                'data = [random.randint(0, 10000) for _ in range(10000)]\n'
                'start = time.time(); bubble_sort(data[:]); print("Bubble:", time.time()-start)\n'
                'start = time.time(); quick_sort(data[:]); print("Quick: ", time.time()-start)\n'
                '```'
            ),
            'external_url': 'https://visualgo.net/ru/sorting',
            'age_groups': ['middle'],
            'topic': 'алгоритмы',
            'difficulty': 'medium',
            'is_published': True,
        },

        # ── Senior (16–17 лет) ─────────────────────────────────────────────
        {
            'slug': 'senior-python-todo-api',
            'title': 'REST API для списка задач на Flask',
            'summary': (
                'Напиши простой REST API: GET /tasks, POST /tasks, DELETE /tasks/<id>. '
                'Данные храни в памяти (список). Протестируй через curl или Postman.'
            ),
            'body': (
                '## Минимальный сервер\n'
                '```python\n'
                'from flask import Flask, request, jsonify\n\n'
                'app = Flask(__name__)\n'
                'tasks = []\n'
                'next_id = 1\n\n'
                '@app.get("/tasks")\n'
                'def get_tasks():\n'
                '    return jsonify(tasks)\n\n'
                '@app.post("/tasks")\n'
                'def create_task():\n'
                '    global next_id\n'
                '    body = request.get_json()\n'
                '    task = {"id": next_id, "title": body["title"], "done": False}\n'
                '    tasks.append(task); next_id += 1\n'
                '    return jsonify(task), 201\n\n'
                '@app.delete("/tasks/<int:task_id>")\n'
                'def delete_task(task_id):\n'
                '    global tasks\n'
                '    tasks = [t for t in tasks if t["id"] != task_id]\n'
                '    return {"ok": True}\n\n'
                'app.run(debug=True)\n'
                '```\n\n'
                '## Усложнения\n'
                '- Добавь PATCH /tasks/<id> для пометки выполненным\n'
                '- Подключи SQLite через sqlite3 вместо списка в памяти\n'
                '- Добавь валидацию: 400, если title отсутствует или пустой'
            ),
            'external_url': 'https://flask.palletsprojects.com/en/stable/quickstart/',
            'age_groups': ['senior'],
            'topic': 'python',
            'difficulty': 'medium',
            'is_published': True,
        },
        {
            'slug': 'senior-js-fetch-weather',
            'title': 'Виджет погоды на JavaScript + Fetch API',
            'summary': (
                'Запроси данные с открытого API wttr.in, распарси JSON и отобрази '
                'температуру, иконку и описание погоды на странице. Практика async/await и DOM.'
            ),
            'body': (
                '## Базовый запрос\n'
                '```javascript\n'
                'async function getWeather(city) {\n'
                '  const res = await fetch(\n'
                '    `https://wttr.in/${city}?format=j1`\n'
                '  );\n'
                '  const data = await res.json();\n'
                '  const current = data.current_condition[0];\n'
                '  return {\n'
                '    temp: current.temp_C,\n'
                '    feels: current.FeelsLikeC,\n'
                '    desc: current.weatherDesc[0].value,\n'
                '  };\n'
                '}\n\n'
                'getWeather("Moscow").then(w => {\n'
                '  document.getElementById("weather").textContent =\n'
                '    `${w.temp}°C, ощущается как ${w.feels}°C — ${w.desc}`;\n'
                '});\n'
                '```\n\n'
                '## Задание\n'
                '- Добавь input для ввода города и кнопку\n'
                '- Покажи спиннер загрузки во время запроса\n'
                '- Обработай ошибку сети через try/catch и покажи сообщение пользователю\n'
                '- Красиво оформи карточку погоды с CSS'
            ),
            'external_url': 'https://wttr.in/:help',
            'age_groups': ['senior'],
            'topic': 'javascript',
            'difficulty': 'medium',
            'is_published': True,
        },
        {
            'slug': 'senior-git-workflow',
            'title': 'Git на практике: ветки, конфликты, PR',
            'summary': (
                'Пройди полный цикл командной разработки: создай ветку, внеси изменения, '
                'намеренно вызови конфликт слияния и разреши его. Обязательный навык для любого разработчика.'
            ),
            'body': (
                '## Упражнение\n'
                '```bash\n'
                '# Инициализируй репозиторий\n'
                'git init my-project && cd my-project\n'
                'echo "# My Project" > README.md\n'
                'git add . && git commit -m "init"\n\n'
                '# Создай две ветки от main\n'
                'git checkout -b feature/alice\n'
                'echo "Alice was here" >> README.md\n'
                'git commit -am "alice: add note"\n\n'
                'git checkout main\n'
                'git checkout -b feature/bob\n'
                'echo "Bob was here" >> README.md\n'
                'git commit -am "bob: add note"\n\n'
                '# Смерджи Alice в main, затем попробуй смерджить Bob\n'
                'git checkout main\n'
                'git merge feature/alice\n'
                'git merge feature/bob  # будет конфликт!\n'
                '```\n\n'
                '## Как разрешить конфликт\n'
                'Открой README.md, найди маркеры `<<<<<<<`, `=======`, `>>>>>>>`. '
                'Выбери нужный вариант, удали маркеры, сохрани файл и выполни:\n'
                '```bash\n'
                'git add README.md && git commit -m "resolve: merge alice and bob"\n'
                '```\n\n'
                '## Изучи дополнительно\n'
                '- git rebase vs git merge\n'
                '- git stash для сохранения незакоммиченных изменений\n'
                '- git log --oneline --graph для красивой истории'
            ),
            'external_url': 'https://learngitbranching.js.org/?locale=ru_RU',
            'age_groups': ['senior'],
            'topic': 'git',
            'difficulty': 'hard',
            'is_published': True,
        },
    ]

    existing_slugs = {row.slug for row in UsefulTask.query.with_entities(UsefulTask.slug).all()}
    added = 0
    for data in tasks:
        if data['slug'] in existing_slugs:
            continue
        db.session.add(UsefulTask(
            slug=data['slug'],
            title=data['title'],
            summary=data['summary'],
            body=data['body'],
            external_url=data.get('external_url'),
            age_groups=data['age_groups'],
            topic=data.get('topic'),
            difficulty=data['difficulty'],
            is_published=data['is_published'],
        ))
        added += 1
    if added:
        db.session.commit()


def seed_all(enable_demo_data: bool = True) -> None:
    if current_app.config.get('SUPERADMIN_BOOTSTRAP', False):
        bootstrap_superadmin()
    seed_achievements()
    cleanup_deprecated_learning_artifacts()
    seed_modules()
    repair_legacy_code_task_validations()
    seed_useful_tasks()
    if enable_demo_data:
        seed_demo_users()
        seed_classes_and_assignments()
