from __future__ import annotations

from ..models.learning import Quiz

VALID_QUIZ_QUESTION_TYPES = {'single', 'multiple', 'order', 'match', 'text'}


def safe_int(value, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def string_list(value) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.splitlines() if item.strip()]
    if not isinstance(value, list):
        return []
    rows: list[str] = []
    for item in value:
        text = str(item or '').strip()
        if text:
            rows.append(text)
    return rows


def normalize_quiz_questions(raw_questions, question_prefix: str = 'quiz-q') -> list[dict]:
    if not isinstance(raw_questions, list):
        return []

    normalized: list[dict] = []
    for index, item in enumerate(raw_questions, start=1):
        if not isinstance(item, dict):
            continue
        qtype = str(item.get('type') or 'single').strip().lower()
        prompt = str(item.get('prompt') or '').strip()
        if qtype not in VALID_QUIZ_QUESTION_TYPES or not prompt:
            continue

        question_id = f'{question_prefix}{index}'

        if qtype in {'single', 'multiple'}:
            options = string_list(item.get('options'))
            if len(options) < 2:
                continue
            raw_correct = item.get('correct')
            raw_indices = raw_correct if isinstance(raw_correct, list) else [raw_correct]
            correct_indices: list[int] = []
            for raw_value in raw_indices:
                try:
                    parsed = int(raw_value)
                except (TypeError, ValueError):
                    continue
                if 0 <= parsed < len(options) and parsed not in correct_indices:
                    correct_indices.append(parsed)
            if qtype == 'single':
                if len(correct_indices) != 1:
                    continue
                correct = [correct_indices[0]]
            else:
                if not correct_indices:
                    continue
                correct = sorted(correct_indices)
            normalized.append({
                'id': question_id,
                'type': qtype,
                'prompt': prompt,
                'options': options,
                'correct': correct,
            })
            continue

        if qtype == 'order':
            items = string_list(item.get('items'))
            correct = string_list(item.get('correct'))
            if len(items) < 2 or len(correct) != len(items) or sorted(correct) != sorted(items):
                continue
            normalized.append({
                'id': question_id,
                'type': qtype,
                'prompt': prompt,
                'items': items,
                'correct': correct,
            })
            continue

        if qtype == 'match':
            # The builder and seeded content use left/right/correct, while an
            # older endpoint accepted pairs.  Accept both contracts and emit
            # the canonical left/right/correct form.
            raw_pairs = item.get('pairs')
            if isinstance(raw_pairs, list):
                pairs = [
                    (str(pair.get('left') or '').strip(), str(pair.get('right') or '').strip())
                    for pair in raw_pairs
                    if isinstance(pair, dict)
                ]
                pairs = [(left, right) for left, right in pairs if left and right]
                left_values = [left for left, _ in pairs]
                right_values = []
                correct_map: dict[str, str] = {}
                for left, right in pairs:
                    if left in correct_map:
                        continue
                    correct_map[left] = right
                    if right not in right_values:
                        right_values.append(right)
            else:
                left_values = string_list(item.get('left'))
                right_values = string_list(item.get('right'))
                raw_correct = item.get('correct')
                correct_map = {
                    str(left).strip(): str(right).strip()
                    for left, right in raw_correct.items()
                    if str(left).strip() and str(right).strip()
                } if isinstance(raw_correct, dict) else {}
            if (
                len(left_values) < 2
                or len(right_values) < 2
                or len(set(left_values)) != len(left_values)
                or len(set(right_values)) != len(right_values)
                or set(correct_map) != set(left_values)
                or any(value not in right_values for value in correct_map.values())
            ):
                continue
            normalized.append({
                'id': question_id,
                'type': qtype,
                'prompt': prompt,
                'left': left_values,
                'right': right_values,
                'correct': correct_map,
            })
            continue

        if qtype == 'text':
            correct_answers = string_list(item.get('correct'))
            if not correct_answers:
                continue
            normalized.append({
                'id': question_id,
                'type': qtype,
                'prompt': prompt,
                'correct': correct_answers,
            })

    return normalized


def build_lesson_quiz(lesson, raw_quiz, lesson_title: str, question_prefix: str = 'quiz-q') -> Quiz | None:
    if not isinstance(raw_quiz, dict) or not raw_quiz.get('enabled'):
        return None

    questions = normalize_quiz_questions(raw_quiz.get('questions'), question_prefix=question_prefix)
    if not questions:
        raise ValueError('Добавьте хотя бы один корректный вопрос в итоговый квиз.')

    return Quiz(
        lesson_id=lesson.id,
        title=str(raw_quiz.get('title') or '').strip() or f'Квиз: {lesson_title}',
        passing_score=safe_int(raw_quiz.get('passing_score'), 70, minimum=0, maximum=100),
        questions=questions,
        xp_reward=safe_int(raw_quiz.get('xp_reward'), 50, minimum=0, maximum=500),
    )
