'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'

import { AdminLessonBuilder } from '@/components/admin-lesson-builder'
import { TeacherLessonBuilder } from '@/components/teacher-lesson-builder'
import { api, getApiErrorMessage } from '@/lib/api'
import type { LessonAuthoringDetail, ModuleItem, TeacherClassDetail, TeacherOverviewData } from '@/types'

function EditorState({
  title,
  description,
  retry,
  backHref,
  loading = false,
}: {
  title: string
  description: string
  retry?: () => void
  backHref: string
  loading?: boolean
}) {
  return (
    <section className='codequest-card mx-auto max-w-3xl p-8 text-center sm:p-10'>
      <p className='brand-eyebrow'>Редактор урока</p>
      <h1 className='mt-3 text-2xl font-black text-slate-900'>{title}</h1>
      <p className='mx-auto mt-3 max-w-xl text-sm leading-7 text-slate-600'>{description}</p>
      <div className='mt-6 flex flex-wrap justify-center gap-3'>
        {retry ? (
          <button
            type='button'
            onClick={retry}
            className='inline-flex min-h-11 items-center gap-2 rounded-full bg-slate-900 px-5 text-sm font-semibold text-white'
          >
            <RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />
            Повторить
          </button>
        ) : null}
        <Link href={backHref} className='inline-flex min-h-11 items-center rounded-full border border-slate-200 bg-white px-5 text-sm font-semibold text-slate-700'>
          К списку уроков
        </Link>
      </div>
    </section>
  )
}

export function AdminLessonEditor({
  lessonId,
  listHref,
}: {
  lessonId: number
  listHref: string
}) {
  const [lesson, setLesson] = useState<LessonAuthoringDetail | null>(null)
  const [modules, setModules] = useState<ModuleItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      api<{ lesson: LessonAuthoringDetail }>(`/admin/lessons/${lessonId}`, undefined, 'required'),
      api<{ modules: ModuleItem[] }>('/admin/modules?page=1&page_size=15', undefined, 'required'),
    ])
      .then(([lessonResult, moduleResult]) => {
        if (cancelled) return
        setLesson(lessonResult.lesson)
        const roadmapModules = moduleResult.modules.filter(module => !module.is_custom_classroom_module)
        setModules(roadmapModules.some(module => module.id === lessonResult.lesson.module.id)
          ? roadmapModules
          : [lessonResult.lesson.module, ...roadmapModules])
      })
      .catch(loadError => {
        if (!cancelled) setError(getApiErrorMessage(loadError, 'Не удалось загрузить урок для редактирования.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lessonId, reloadToken])

  if (loading && (!lesson || !modules)) {
    return <EditorState title='Загружаем урок' description='Получаем актуальную версию и структуру модуля.' backHref={listHref} loading />
  }
  if (error || !lesson || !modules) {
    return (
      <EditorState
        title='Урок не загрузился'
        description={error || 'Актуальная версия урока недоступна.'}
        retry={() => setReloadToken(value => value + 1)}
        backHref={listHref}
      />
    )
  }

  return (
    <AdminLessonBuilder
      modules={modules}
      editingLesson={lesson}
      cancelHref={listHref}
      lessonListHref={listHref}
    />
  )
}

export function TeacherLessonEditor({ lessonId }: { lessonId: number }) {
  const [lesson, setLesson] = useState<LessonAuthoringDetail | null>(null)
  const [overview, setOverview] = useState<TeacherOverviewData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      api<{ lesson: LessonAuthoringDetail }>(`/teacher/lessons/${lessonId}`, undefined, 'required'),
      api<TeacherOverviewData>('/teacher/overview?page=1&page_size=15', undefined, 'required'),
    ])
      .then(async ([lessonResult, overviewResult]) => {
        if (cancelled) return
        const classroomId = lessonResult.lesson.module?.custom_classroom_id
        let nextOverview = overviewResult
        if (typeof classroomId === 'number' && !overviewResult.classes.some(item => item.id === classroomId)) {
          const classDetail = await api<TeacherClassDetail>(
            `/teacher/classes/${classroomId}?students_page=1&assignments_page=1&page_size=15`,
            undefined,
            'required',
          )
          nextOverview = { ...overviewResult, classes: [classDetail.classroom, ...overviewResult.classes] }
        }
        if (cancelled) return
        setLesson(lessonResult.lesson)
        setOverview(nextOverview)
      })
      .catch(loadError => {
        if (!cancelled) setError(getApiErrorMessage(loadError, 'Не удалось загрузить урок для редактирования.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [lessonId, reloadToken])

  if (loading && (!lesson || !overview)) {
    return <EditorState title='Загружаем урок' description='Получаем актуальную версию урока и данные класса.' backHref='/teacher/lessons' loading />
  }
  if (error || !lesson || !overview) {
    return (
      <EditorState
        title='Урок не загрузился'
        description={error || 'Актуальная версия урока недоступна.'}
        retry={() => setReloadToken(value => value + 1)}
        backHref='/teacher/lessons'
      />
    )
  }

  return (
    <TeacherLessonBuilder
      initialClasses={overview.classes}
      initialPagination={overview.classes_pagination}
      editingLesson={lesson}
      cancelHref='/teacher/lessons'
      lessonListHref='/teacher/lessons'
    />
  )
}
