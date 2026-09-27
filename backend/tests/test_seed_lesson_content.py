from __future__ import annotations

import sys
import unittest
from pathlib import Path

from flask import Flask


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _build_modules() -> list[dict]:
    from app.seed.bootstrap import (
        _lesson_payload,
        _question_match,
        _question_multiple,
        _question_order,
        _question_single,
        _stdio_validation,
    )
    from app.seed.learning_content import build_learning_modules

    return build_learning_modules(
        _lesson_payload,
        _question_single,
        _question_multiple,
        _question_order,
        _question_match,
        _stdio_validation,
    )


class SeedLessonContentTests(unittest.TestCase):
    def test_every_seed_lesson_has_unique_explanation_example_and_practice(self):
        modules = _build_modules()

        self.assertEqual(len(modules), 30)
        lessons = [
            (module, lesson_index, lesson)
            for module in modules
            for lesson_index, lesson in enumerate(module["lessons"], start=1)
        ]
        self.assertEqual(len(lessons), 150)
        self.assertEqual(
            {
                age_group: sum(
                    len(module["lessons"])
                    for module in modules
                    if module["age_group"] == age_group
                )
                for age_group in ("junior", "middle", "senior")
            },
            {"junior": 50, "middle": 50, "senior": 50},
        )

        explanations: set[str] = set()
        examples: set[str] = set()
        practices: set[str] = set()
        single_correct_positions: set[int] = set()
        multiple_distractor_positions: set[int] = set()
        old_generic_fragments = {
            "Похожий тренировочный пример",
            "Нажимай Далее и смотри",
            "Попробуй изменить одну команду",
        }

        for module, _lesson_index, lesson in lessons:
            theory = lesson["theory_blocks"]
            self.assertEqual(len(theory), 3)
            self.assertEqual(
                [block["title"] for block in theory],
                [
                    lesson["title"],
                    "Объяснение темы",
                    "Главное, что нужно запомнить",
                ],
            )
            self.assertEqual(theory[0]["type"], "hero")
            self.assertEqual(theory[1]["type"], "text")
            self.assertEqual(theory[2]["type"], "list")
            self.assertEqual(len(theory[2]["items"]), 3)

            example_steps = lesson["interactive_steps"]
            self.assertEqual(len(example_steps), 3)
            self.assertTrue(
                all(step.get("title") and step.get("text") for step in example_steps)
            )

            task = lesson["task"]
            self.assertTrue(task["title"].strip())
            self.assertTrue(task["prompt"].strip())
            self.assertEqual(len(task["hints"]), 3)
            if module["age_group"] == "junior":
                self.assertEqual(task["starter_code"], "")
                self.assertIn("keywords", task["validation"])
                self.assertTrue(task["validation"]["require_all_keywords"])
                self.assertEqual(task["validation"]["minimum_answer_length"], 80)
            elif task["starter_code"]:
                self.assertEqual(
                    task["validation"]["language"],
                    "python"
                    if module["age_group"] == "middle"
                    else "javascript",
                )
                self.assertEqual(
                    task["validation"]["evaluation_mode"], "stdin_stdout"
                )
                self.assertTrue(task["validation"]["tests"])
            else:
                self.assertTrue(task["validation"]["require_all_keywords"])
                self.assertEqual(
                    task["validation"]["minimum_answer_length"],
                    100 if module["age_group"] == "middle" else 120,
                )
            if not task["starter_code"]:
                self.assertIn("Ответ должен содержать не меньше", task["prompt"])

            quiz = lesson["quiz"]
            self.assertEqual([question["type"] for question in quiz], [
                "single",
                "multiple",
                "order",
            ])
            single_correct_positions.add(quiz[0]["correct"][0])
            multiple_distractor_positions.add(
                next(
                    index
                    for index in range(len(quiz[1]["options"]))
                    if index not in quiz[1]["correct"]
                )
            )
            expected_step_order = [step["title"] for step in example_steps]
            self.assertCountEqual(quiz[2]["items"], expected_step_order)
            self.assertEqual(quiz[2]["correct"], expected_step_order)
            self.assertNotEqual(quiz[2]["items"], quiz[2]["correct"])

            explanation = theory[1]["text"]
            example = "\n".join(
                f'{step["title"]}\n{step["text"]}' for step in example_steps
            )
            practice = task["prompt"]
            self.assertFalse(
                any(
                    fragment in "\n".join((explanation, example, practice))
                    for fragment in old_generic_fragments
                )
            )
            explanations.add(explanation)
            examples.add(example)
            practices.add(practice)

        self.assertEqual(len(explanations), 150)
        self.assertEqual(len(examples), 150)
        self.assertEqual(len(practices), 150)
        self.assertEqual(single_correct_positions, {0, 1, 2, 3})
        self.assertEqual(multiple_distractor_positions, {0, 1, 2, 3})

    def test_reseeding_updates_content_in_place_and_preserves_links(self):
        from app import models  # noqa: F401
        from app.core.code_judge import judge_task_submission
        from app.core.db import db
        from app.models.learning import (
            Assignment,
            Classroom,
            Lesson,
            Module,
            Quiz,
            Task,
            UserProgress,
        )
        from app.models.user import User, UserRole
        from app.seed.bootstrap import seed_modules

        app = Flask(__name__)
        app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite://",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
        )
        db.init_app(app)

        with app.app_context():
            db.create_all()
            seed_modules()
            self.assertEqual(Module.query.count(), 30)
            self.assertEqual(Lesson.query.count(), 150)

            lesson = Lesson.query.filter_by(
                slug="junior-digital-start-lesson-1"
            ).one()
            task = Task.query.filter_by(lesson_id=lesson.id).order_by(Task.id).first()
            quiz = Quiz.query.filter_by(lesson_id=lesson.id).order_by(Quiz.id).first()
            self.assertIsNotNone(task)
            self.assertIsNotNone(quiz)

            original_ids = (lesson.id, task.id, quiz.id)
            lesson.is_published = False
            lesson.module.is_published = False
            lesson.summary = "Устаревшее объяснение"
            task.prompt = "Устаревшая практика"
            task.xp_reward = 99
            quiz.questions = []
            quiz.xp_reward = 101

            teacher = User(
                full_name="Teacher",
                email="teacher-seed@example.com",
                password_hash="test",
                role=UserRole.TEACHER,
            )
            student = User(
                full_name="Student",
                email="student-seed@example.com",
                password_hash="test",
                role=UserRole.STUDENT,
                age_group="junior",
            )
            db.session.add_all([teacher, student])
            db.session.flush()
            classroom = Classroom(
                name="Seed class",
                code="SEED01",
                teacher_id=teacher.id,
            )
            db.session.add(classroom)
            db.session.flush()
            assignment = Assignment(
                classroom_id=classroom.id,
                lesson_id=lesson.id,
                title="Existing assignment",
                description="Must keep the same lesson link",
            )
            progress = UserProgress(
                user_id=student.id,
                lesson_id=lesson.id,
                status="completed",
                score=88,
            )
            custom_module = Module(
                slug="teacher-class-999-custom",
                title="Custom module",
                description="Created by a teacher",
                age_group="junior",
                order_index=999,
            )
            db.session.add_all([assignment, progress, custom_module])
            db.session.flush()
            custom_lesson = Lesson(
                module_id=custom_module.id,
                slug="teacher-class-999-custom-lesson-1",
                title="Custom lesson",
                summary="Teacher content",
                theory_blocks=[{"type": "text", "title": "Own", "text": "Keep"}],
                interactive_steps=[],
                order_index=1,
            )
            db.session.add(custom_lesson)
            db.session.flush()
            custom_task = Task(
                lesson_id=custom_lesson.id,
                task_type="text",
                title="Teacher practice",
                prompt="Teacher-owned task content",
                validation={"evaluation_mode": "manual"},
                hints=["Own hint"],
                xp_reward=77,
            )
            custom_quiz = Quiz(
                lesson_id=custom_lesson.id,
                title="Teacher quiz",
                questions=[
                    {
                        "id": "teacher-q1",
                        "type": "single",
                        "prompt": "Teacher question",
                        "options": ["Yes", "No"],
                        "correct": [0],
                    }
                ],
                xp_reward=66,
            )
            db.session.add_all([custom_task, custom_quiz])
            db.session.commit()

            canonical_module_slugs = {
                module["slug"] for module in _build_modules()
            }
            module_snapshot = {
                row.slug: (row.id, row.is_published)
                for row in Module.query.filter(
                    Module.slug.in_(canonical_module_slugs)
                ).all()
            }
            lesson_snapshot = {}
            for row in (
                Lesson.query.join(Module)
                .filter(Module.slug.in_(canonical_module_slugs))
                .all()
            ):
                row_task = (
                    Task.query.filter_by(lesson_id=row.id)
                    .order_by(Task.id)
                    .first()
                )
                row_quiz = (
                    Quiz.query.filter_by(lesson_id=row.id)
                    .order_by(Quiz.id)
                    .first()
                )
                lesson_snapshot[row.slug] = (
                    row.id,
                    row.module_id,
                    row.duration_minutes,
                    row.passing_score,
                    row.is_published,
                    row_task.id,
                    row_task.xp_reward,
                    row_quiz.id,
                    row_quiz.xp_reward,
                )

            seed_modules()
            seed_modules()

            updated_lesson = Lesson.query.filter_by(
                slug="junior-digital-start-lesson-1"
            ).one()
            updated_task = (
                Task.query.filter_by(lesson_id=updated_lesson.id)
                .order_by(Task.id)
                .first()
            )
            updated_quiz = (
                Quiz.query.filter_by(lesson_id=updated_lesson.id)
                .order_by(Quiz.id)
                .first()
            )
            db.session.refresh(assignment)
            db.session.refresh(progress)
            db.session.refresh(custom_lesson)
            db.session.refresh(custom_task)
            db.session.refresh(custom_quiz)

            self.assertEqual(
                (updated_lesson.id, updated_task.id, updated_quiz.id),
                original_ids,
            )
            self.assertEqual(updated_lesson.summary, _build_modules()[0]["lessons"][0]["summary"])
            self.assertEqual(
                updated_lesson.theory_blocks[1]["title"], "Объяснение темы"
            )
            self.assertNotEqual(updated_task.prompt, "Устаревшая практика")
            self.assertTrue(updated_quiz.questions)
            self.assertEqual(updated_task.xp_reward, 99)
            self.assertEqual(updated_quiz.xp_reward, 101)
            self.assertFalse(updated_lesson.is_published)
            self.assertFalse(updated_lesson.module.is_published)
            self.assertEqual(assignment.lesson_id, updated_lesson.id)
            self.assertEqual(progress.lesson_id, updated_lesson.id)
            self.assertEqual(progress.score, 88)
            self.assertEqual(custom_lesson.summary, "Teacher content")
            self.assertEqual(custom_task.prompt, "Teacher-owned task content")
            self.assertEqual(custom_task.xp_reward, 77)
            self.assertEqual(custom_quiz.title, "Teacher quiz")
            self.assertEqual(custom_quiz.xp_reward, 66)
            self.assertEqual(Module.query.count(), 31)
            self.assertEqual(Lesson.query.count(), 151)

            self.assertEqual(
                {
                    row.slug: (row.id, row.is_published)
                    for row in Module.query.filter(
                        Module.slug.in_(canonical_module_slugs)
                    ).all()
                },
                module_snapshot,
            )
            protected_lesson_fields = {}
            for row in (
                Lesson.query.join(Module)
                .filter(Module.slug.in_(canonical_module_slugs))
                .all()
            ):
                row_task = (
                    Task.query.filter_by(lesson_id=row.id)
                    .order_by(Task.id)
                    .first()
                )
                row_quiz = (
                    Quiz.query.filter_by(lesson_id=row.id)
                    .order_by(Quiz.id)
                    .first()
                )
                protected_lesson_fields[row.slug] = (
                    row.id,
                    row.module_id,
                    row.duration_minutes,
                    row.passing_score,
                    row.is_published,
                    row_task.id,
                    row_task.xp_reward,
                    row_quiz.id,
                    row_quiz.xp_reward,
                )
            self.assertEqual(protected_lesson_fields, lesson_snapshot)

            validation = updated_task.normalized_validation(include_private=True)
            keyword_only = ", ".join(validation["keywords"])
            short_report = judge_task_submission(updated_task, keyword_only)
            self.assertFalse(short_report["passed"])
            self.assertLess(
                short_report["answer_length"],
                short_report["minimum_answer_length"],
            )

            missing_keyword_answer = (
                "Устройство получает ввод от человека, выполняет понятные "
                "команды и затем подробно объясняет выполненные действия. "
                "Такой ответ достаточно длинный, но намеренно не называет итог."
            )
            missing_keyword_report = judge_task_submission(
                updated_task,
                missing_keyword_answer,
            )
            self.assertFalse(missing_keyword_report["passed"])
            self.assertTrue(missing_keyword_report["missing_keywords"])

            complete_answer = (
                "Устройство получает ввод от человека, выполняет заданные "
                "команды и показывает результат. Например, калькулятор получает "
                "два числа, складывает их и выводит проверяемый итог на экран."
            )
            complete_report = judge_task_submission(updated_task, complete_answer)
            self.assertTrue(complete_report["passed"])
            self.assertEqual(complete_report["score"], 100)

            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
