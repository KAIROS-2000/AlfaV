# Teacher Dashboard UI Freeze

This note freezes the teacher-facing behavior that must remain intact while the dashboard and lesson-builder UI are reorganized.

## Existing Teacher Actions

- Create a class with a name and optional description.
- Select a class and keep all downstream panels scoped to that selected class.
- Copy the selected class code.
- Load pending join requests.
- Approve or reject join requests through the existing confirmation flow.
- View enrolled students for the selected class.
- Inspect selected-class stats and the practice heatmap.
- Browse catalog lessons and teacher-created lessons.
- Create a teacher lesson from the shared lesson builder.
- Prefill a teacher lesson from an existing lesson.
- Create an assignment for the selected class.
- Apply assignment templates to the assignment form.
- Select an assignment from the selected class.
- Load and review assignment submissions.
- Grade a submission as correct.
- Mark a submission as needing revision.
- Keep feedback comments attached to the existing grading actions.

## Contracts To Preserve

- Teacher overview, class detail, lesson catalog, assignment, join-request, submission, and grading endpoints stay unchanged.
- Assignment creation keeps the existing payload fields and validation rules.
- Lesson creation continues to use `SharedLessonBuilder`; teacher and admin builders must not fork.
- Admin module lesson creation keeps `publish_module_if_needed`.
- Admin-created lessons still cannot use manual review.
- Junior lessons still cannot use code practice.
- Code practice still requires at least one complete judge test.
- Keyword checks still require answer keywords.
- Quiz payloads still pass through the existing normalization rules before submit.

## Redesign Scope

The UI may reorganize layout, empty states, filters, inline validation, action placement, and explanatory copy. It must not change backend business logic or request/response contracts unless the backend tests are deliberately updated in the same change.
