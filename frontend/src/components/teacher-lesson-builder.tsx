'use client'

import { api } from '@/lib/api'
import type { ClassroomItem, LessonAuthoringDetail, PaginationMeta, TeacherClassesResponse } from '@/types'
import { SERVER_PAGE_SIZE } from '@/components/five-item-navigator'
import { useEffect, useState } from 'react'

import { SharedLessonBuilder } from './shared-lesson-builder'
import { buildLessonUpdateData } from './lesson-builder-shared'

interface TeacherLessonBuilderProps {
  initialClasses: ClassroomItem[]
  initialClassId?: number | null
  sourceLessonId?: number | null
  editingLesson?: LessonAuthoringDetail | null
  cancelHref?: string | null
  lessonListHref?: string | null
  initialPagination?: PaginationMeta | null
}

export function TeacherLessonBuilder({
  initialClasses,
  initialClassId = null,
  sourceLessonId = null,
  editingLesson = null,
  cancelHref = '/teacher',
  lessonListHref = '/teacher/lessons',
  initialPagination = null,
}: TeacherLessonBuilderProps) {
  const [classes, setClasses] = useState(initialClasses)
  const [pagination, setPagination] = useState(initialPagination)
  const [page, setPage] = useState(initialPagination?.page ?? 1)
  const [classesLoading, setClassesLoading] = useState(false)

  useEffect(() => {
    if (initialPagination && page === initialPagination.page) return
    let cancelled = false
    setClassesLoading(true)
    api<TeacherClassesResponse>(`/teacher/classes?page=${page}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required')
      .then(result => {
        if (cancelled) return
        setClasses(result.classes)
        setPagination(result.pagination)
      })
      .finally(() => {
        if (!cancelled) setClassesLoading(false)
      })
    return () => { cancelled = true }
  }, [initialPagination, page])

  return (
    <SharedLessonBuilder
      mode='teacher'
      features={{
        drafts: !editingLesson,
        sourcePrefill: !editingLesson,
        publishToggle: false,
        insertPosition: false,
        quiz: true,
        help: true,
      }}
      targetConfig={{
        kind: 'classroom',
        classes,
        initialClassId: editingLesson?.module?.custom_classroom_id ?? initialClassId,
        sourceLessonId: editingLesson ? null : sourceLessonId,
        draftKey: 'progyx_teacher_lesson_builder_v2',
        createTargetHref: '/teacher',
        pagination,
        loading: classesLoading,
        onPageChange: setPage,
      }}
      cancelHref={cancelHref}
      editing={editingLesson ? { lesson: editingLesson } : undefined}
      lessonListHref={lessonListHref}
      publishCreatedLesson={async ({ lesson, target }) => {
        if (target.kind !== 'classroom') {
          throw new Error('Некорректный класс для публикации урока.')
        }
        await api(
          `/teacher/lessons/${lesson.id}/share`,
          {
            method: 'POST',
            body: JSON.stringify({
              classroom_id: target.classroomId,
              ...(typeof lesson.version === 'number' ? { version: lesson.version } : {}),
            }),
          },
          'required',
        )
        return 'Урок открыт классу. Ученики получили одно уведомление.'
      }}
      submitLesson={async ({ target, lesson, saveDraft, draftPayload }) => {
        if (target.kind !== 'classroom') {
          throw new Error('Некорректная цель сохранения урока.')
        }

        const data = await api<{ lesson: LessonAuthoringDetail }>(
          `/teacher/classes/${target.classroomId}/lessons`,
          {
            method: 'POST',
            body: JSON.stringify({
              ...lesson,
              save_draft: saveDraft,
              ...(draftPayload ? { draft_payload: draftPayload } : {}),
            }),
          },
          'required',
        )

        return {
          lesson: data.lesson,
          authoringLesson: data.lesson,
          successMessage: 'Черновик урока сохранён. Ученики не получили уведомления и не видят его, пока вы явно не откроете урок классу.',
        }
      }}
      updateLesson={async ({ lessonId, version, lesson, saveDraft, draftPayload }) => {
        const data = await api<{ lesson: LessonAuthoringDetail }>(
          `/teacher/lessons/${lessonId}`,
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
      publishSavedLesson={async ({ lesson, target }) => {
        if (target.kind !== 'classroom') {
          throw new Error('Некорректный класс для публикации урока.')
        }
        const data = await api<{ lesson: LessonAuthoringDetail }>(
          `/teacher/lessons/${lesson.id}/share`,
          {
            method: 'POST',
            body: JSON.stringify({ classroom_id: target.classroomId, version: lesson.version }),
          },
          'required',
        )
        return {
          lesson: data.lesson,
          successMessage: 'Урок открыт классу. Ученики получили одно уведомление.',
        }
      }}
    />
  )
}
