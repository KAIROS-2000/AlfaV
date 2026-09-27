from __future__ import annotations

from .lesson_specs_junior import JUNIOR_LESSON_SPECS
from .lesson_specs_middle import MIDDLE_LESSON_SPECS
from .lesson_specs_senior import SENIOR_LESSON_SPECS


LESSON_SPECS: dict[str, dict] = {
    **JUNIOR_LESSON_SPECS,
    **MIDDLE_LESSON_SPECS,
    **SENIOR_LESSON_SPECS,
}


def validate_lesson_specs(expected_lessons: dict[str, str]) -> None:
    expected_slugs = set(expected_lessons)
    actual_slugs = set(LESSON_SPECS)
    missing = sorted(expected_slugs - actual_slugs)
    extra = sorted(actual_slugs - expected_slugs)
    if missing or extra:
        raise ValueError(
            "Seed lesson specification coverage mismatch: "
            f"missing={missing}, extra={extra}"
        )

    errors: list[str] = []
    unique_fields: dict[str, dict[str, str]] = {
        "objective": {},
        "explanation": {},
        "example": {},
        "practice": {},
    }

    def require_unique(field: str, value: str, slug: str) -> None:
        normalized = " ".join(value.lower().split())
        previous_slug = unique_fields[field].get(normalized)
        if previous_slug:
            errors.append(
                f"{slug}: {field} duplicates content from {previous_slug}"
            )
        else:
            unique_fields[field][normalized] = slug

    for slug, expected_title in expected_lessons.items():
        spec = LESSON_SPECS[slug]
        if spec.get("title") != expected_title:
            errors.append(
                f'{slug}: title must be "{expected_title}", got {spec.get("title")!r}'
            )

        for field in ("objective", "explanation"):
            value = spec.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{slug}: {field} must be a non-empty string")
            else:
                require_unique(field, value, slug)

        key_points = spec.get("key_points")
        if (
            not isinstance(key_points, list)
            or len(key_points) != 3
            or any(not isinstance(item, str) or not item.strip() for item in key_points)
            or len(set(key_points)) != 3
        ):
            errors.append(f"{slug}: key_points must contain 3 unique non-empty strings")

        example_steps = spec.get("example_steps")
        if not isinstance(example_steps, list) or len(example_steps) != 3:
            errors.append(f"{slug}: example_steps must contain exactly 3 steps")
        else:
            example_fingerprint: list[str] = []
            step_titles: list[str] = []
            for index, step in enumerate(example_steps, start=1):
                if not isinstance(step, dict):
                    errors.append(f"{slug}: example step {index} must be an object")
                    continue
                for field in ("title", "text"):
                    value = step.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(
                            f"{slug}: example step {index} {field} must be non-empty"
                        )
                    else:
                        example_fingerprint.append(value)
                        if field == "title":
                            step_titles.append(value)
            if len(step_titles) == 3 and len(set(step_titles)) != 3:
                errors.append(f"{slug}: example step titles must be unique")
            if len(example_fingerprint) == 6:
                require_unique("example", "\n".join(example_fingerprint), slug)

        practice = spec.get("practice")
        if not isinstance(practice, dict):
            errors.append(f"{slug}: practice must be an object")
            continue
        for field in ("title", "prompt"):
            value = practice.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{slug}: practice {field} must be non-empty")
        practice_prompt = practice.get("prompt")
        if isinstance(practice_prompt, str) and practice_prompt.strip():
            require_unique("practice", practice_prompt, slug)
        hints = practice.get("hints")
        if (
            not isinstance(hints, list)
            or len(hints) != 3
            or any(not isinstance(item, str) or not item.strip() for item in hints)
        ):
            errors.append(f"{slug}: practice must contain exactly 3 non-empty hints")

        kind = practice.get("kind")
        if kind == "text":
            keywords = practice.get("keywords")
            if (
                not isinstance(keywords, list)
                or not 3 <= len(keywords) <= 5
                or any(
                    not isinstance(item, str)
                    or not item.strip()
                    or item != item.lower()
                    for item in keywords
                )
            ):
                errors.append(
                    f"{slug}: text practice needs 3-5 lowercase non-empty keywords"
                )
            elif isinstance(practice_prompt, str):
                missing_keywords = [
                    keyword
                    for keyword in keywords
                    if keyword not in practice_prompt.lower()
                ]
                if missing_keywords:
                    errors.append(
                        f"{slug}: practice prompt must explicitly request keywords "
                        f"{missing_keywords}"
                    )
        elif kind == "code":
            language = practice.get("language")
            if language not in {"python", "javascript"}:
                errors.append(f"{slug}: unsupported code language {language!r}")
            expected_language = (
                "python"
                if slug.startswith("middle-")
                else "javascript"
                if slug.startswith("senior-")
                else None
            )
            if language != expected_language:
                errors.append(
                    f"{slug}: code practice language must be {expected_language!r}"
                )
            starter_code = practice.get("starter_code")
            if not isinstance(starter_code, str) or not starter_code.strip():
                errors.append(f"{slug}: code practice requires starter_code")
            elif "TODO" not in starter_code:
                errors.append(
                    f"{slug}: starter_code must contain an explicit TODO for the learner"
                )
            tests = practice.get("tests")
            if not isinstance(tests, list) or not 1 <= len(tests) <= 3:
                errors.append(f"{slug}: code practice requires from 1 to 3 tests")
            else:
                for index, test in enumerate(tests, start=1):
                    if not isinstance(test, dict):
                        errors.append(f"{slug}: test {index} must be an object")
                        continue
                    if not str(test.get("label") or "").strip():
                        errors.append(f"{slug}: test {index} requires a label")
                    if "input" not in test or "expected" not in test:
                        errors.append(
                            f"{slug}: test {index} requires input and expected fields"
                        )
        else:
            errors.append(f"{slug}: practice kind must be text or code")

    if errors:
        preview = "; ".join(errors[:20])
        suffix = f"; and {len(errors) - 20} more" if len(errors) > 20 else ""
        raise ValueError(f"Invalid seed lesson specifications: {preview}{suffix}")


def get_lesson_spec(lesson_slug: str) -> dict:
    try:
        return LESSON_SPECS[lesson_slug]
    except KeyError as exc:
        raise ValueError(
            f'No explicit content specification exists for seed lesson "{lesson_slug}".'
        ) from exc
