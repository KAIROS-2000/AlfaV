'use client'

import { api } from '@/lib/api'
import type { LessonAuthoringDetail, ModuleItem, PaginationMeta } from '@/types'
import { SharedLessonBuilder } from './shared-lesson-builder'
import { buildLessonUpdateData } from './lesson-builder-shared'

interface AdminLessonBuilderProps {
  modules: ModuleItem[]
  onReload?: () => Promise<void> | void
  editingLesson?: LessonAuthoringDetail | null
  cancelHref?: string | null
  lessonListHref?: string | null
  modulesPagination?: PaginationMeta | null
  modulesLoading?: boolean
  onModulesPageChange?: (page: number) => void
}

interface CreateLessonResponse {
  lesson: LessonAuthoringDetail
  roadmap_visible: boolean
  module: ModuleItem
}

export function AdminLessonBuilder({
  modules,
  onReload,
  editingLesson = null,
  cancelHref = null,
  lessonListHref = '#lesson-drafts',
  modulesPagination = null,
  modulesLoading = false,
  onModulesPageChange,
}: AdminLessonBuilderProps) {
  return (
    <SharedLessonBuilder
      mode='admin'
      features={{
        drafts: false,
        sourcePrefill: false,
        publishToggle: false,
        insertPosition: true,
        quiz: true,
        help: false,
      }}
      targetConfig={{
        kind: 'module',
        modules,
        pagination: modulesPagination,
        loading: modulesLoading,
        onPageChange: onModulesPageChange,
      }}
      cancelHref={cancelHref}
      editing={editingLesson ? { lesson: editingLesson } : undefined}
      lessonListHref={lessonListHref}
      submitLesson={async ({ target, lesson, saveDraft, draftPayload }) => {
        if (target.kind !== 'module') {
          throw new Error('Некорректная цель сохранения урока.')
        }

        const data = await api<CreateLessonResponse>(
          `/admin/modules/${target.moduleId}/lessons`,
          {
            method: 'POST',
            body: JSON.stringify({
              title: lesson.title,
              summary: lesson.summary,
              content_format: lesson.content_format,
              authoring_metadata: lesson.authoring_metadata,
              theory_text: lesson.theory_text,
              key_points: lesson.key_points,
              interactive_steps: lesson.interactive_steps,
              duration_minutes: lesson.duration_minutes,
              passing_score: lesson.passing_score,
              insert_position: target.insertPosition,
              // A lesson is created as a draft. Publishing the module must be
              // an explicit, separate operation.
              publish_module_if_needed: false,
              task: {
                enabled: lesson.practice_enabled,
                task_type: lesson.task_type,
                title: lesson.task_title,
                prompt: lesson.task_prompt,
                evaluation_mode: lesson.practice_enabled ? lesson.evaluation_mode : 'manual',
                language: lesson.task_type === 'code' ? lesson.programming_language : null,
                keywords: lesson.evaluation_mode === 'keywords' ? lesson.answer_keywords : '',
                starter_code: lesson.task_type === 'code' ? lesson.starter_code : '',
                hints: lesson.task_hints,
                tests: lesson.task_type === 'code' ? lesson.judge_tests : [],
                time_limit_ms: lesson.task_type === 'code' ? lesson.time_limit_ms : null,
                memory_limit_mb: lesson.task_type === 'code' ? lesson.memory_limit_mb : null,
              },
              quiz: lesson.quiz,
              save_draft: saveDraft,
              ...(draftPayload ? { draft_payload: draftPayload } : {}),
            }),
          },
          'required',
        )

        return {
          lesson: data.lesson,
          authoringLesson: data.lesson,
          successMessage: 'Черновик урока сохранён. Ученики его не видят, пока вы не опубликуете урок отдельным действием.',
          nextInsertPosition: String((data.module.lessons?.length || 0) + 1),
        }
      }}
      updateLesson={async ({ lessonId, version, lesson, saveDraft, draftPayload }) => {
        const data = await api<{ lesson: LessonAuthoringDetail }>(
          `/admin/lessons/${lessonId}`,
          {
            method: 'PATCH',
            body: JSON.stringify({
              ...buildLessonUpdateData(lesson),
              version,
              save_draft: saveDraft,
              ...(draftPayload ? { draft_payload: draftPayload } : {}),
            }),
          },
          'required',
        )
        return data.lesson
      }}
      onCreated={async () => {
        await onReload?.()
      }}
      publishCreatedLesson={async ({ lesson }) => {
        const data = await api<{ roadmap_visible: boolean }>(
          `/admin/lessons/${lesson.id}/publish`,
          {
            method: 'POST',
            body: JSON.stringify(
              typeof lesson.version === 'number' ? { version: lesson.version } : {},
            ),
          },
          'required',
        )
        await onReload?.()
        return data.roadmap_visible
          ? 'Урок опубликован и доступен ученикам.'
          : 'Урок опубликован, но модуль пока скрыт от учеников.'
      }}
      publishSavedLesson={async ({ lesson }) => {
        const data = await api<{ lesson: LessonAuthoringDetail; roadmap_visible: boolean }>(
          `/admin/lessons/${lesson.id}/publish`,
          { method: 'POST', body: JSON.stringify({ version: lesson.version }) },
          'required',
        )
        await onReload?.()
        return {
          lesson: data.lesson,
          successMessage: data.roadmap_visible
            ? 'Урок опубликован и доступен ученикам.'
            : 'Урок опубликован, но модуль пока скрыт от учеников.',
        }
      }}
    />
  )
}
