'use client'

import Link from 'next/link'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { BookOpen, Eye, FilePenLine, RefreshCw, Rocket, X } from 'lucide-react'

import { api, getApiErrorMessage } from '@/lib/api'
import { FiveItemPager, SERVER_PAGE_SIZE, useFiveItemWindow } from '@/components/five-item-navigator'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import type { ClassroomItem, LessonAuthoringListItem, LessonLifecycleListResponse, PaginationMeta } from '@/types'

type LifecycleScope = 'admin' | 'teacher'

interface LifecycleListsProps {
  scope: LifecycleScope
  editBaseHref: string
  initialClasses?: ClassroomItem[] | null
  initialClassesPagination?: PaginationMeta | null
}

interface PublishCandidate {
  lesson: LessonAuthoringListItem
  classroomId?: number | null
}

function formatUpdatedAt(value: string | null | undefined) {
  if (!value) return 'Дата изменения пока не указана'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Дата изменения пока не указана'
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function LessonListEmpty({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className='flex min-h-48 flex-col items-center justify-center rounded-[24px] border border-dashed border-slate-300 bg-slate-50/70 px-5 py-8 text-center'>
      <p className='text-base font-bold text-slate-900'>{title}</p>
      <p className='mt-2 max-w-md text-sm leading-6 text-slate-600'>{description}</p>
      {action ? <div className='mt-4'>{action}</div> : null}
    </div>
  )
}

function LessonCard({
  lesson,
  scope,
  editBaseHref,
  onPublish,
}: {
  lesson: LessonAuthoringListItem
  scope: LifecycleScope
  editBaseHref: string
  onPublish: (lesson: LessonAuthoringListItem) => void
}) {
  const isDraft = lesson.status === 'draft'
  const moduleHidden = lesson.module_is_published === false
  const context = scope === 'teacher'
    ? lesson.classroom_name || lesson.module_title || 'Ваш класс'
    : lesson.module_title || 'Учебный модуль'

  return (
    <article className='flex min-w-0 flex-col rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm'>
      <div className='flex flex-wrap items-start justify-between gap-3'>
        <div className='min-w-0'>
          <p className='break-words text-lg font-bold text-slate-900'>{lesson.title || 'Урок без названия'}</p>
          <p className='mt-1 text-sm text-slate-500'>{context}</p>
        </div>
        <span className={isDraft
          ? 'rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800'
          : 'rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800'}
        >
          {isDraft ? 'Черновик' : 'Опубликован'}
        </span>
      </div>

      <p className='mt-4 min-h-12 break-words text-sm leading-6 text-slate-600'>
        {lesson.summary || 'Описание ещё не добавлено — продолжите редактирование, чтобы заполнить его.'}
      </p>

      <div className='mt-4 flex flex-wrap gap-2 text-xs font-semibold text-slate-600'>
        <span className='rounded-full bg-slate-100 px-3 py-1.5'>Обновлён: {formatUpdatedAt(lesson.updated_at)}</span>
        {moduleHidden ? (
          <span className='rounded-full bg-amber-50 px-3 py-1.5 text-amber-800'>Модуль пока скрыт</span>
        ) : null}
      </div>

      <div className='mt-5 flex flex-wrap gap-2'>
        <Link
          href={`${editBaseHref}/${lesson.id}/edit`}
          className='inline-flex min-h-10 items-center justify-center gap-2 rounded-full bg-slate-900 px-4 text-sm font-semibold text-white transition hover:bg-slate-800'
        >
          <FilePenLine className='h-4 w-4' />
          {isDraft ? 'Продолжить редактирование' : 'Редактировать'}
        </Link>
        {isDraft ? (
          <button
            type='button'
            onClick={() => onPublish(lesson)}
            className='inline-flex min-h-10 items-center justify-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-4 text-sm font-semibold text-sky-800 transition hover:border-sky-300'
          >
            <Rocket className='h-4 w-4' />
            {scope === 'teacher' ? 'Открыть классу' : 'Опубликовать'}
          </button>
        ) : (
          <Link
            href={`/lessons/${lesson.id}`}
            className='inline-flex min-h-10 items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:border-slate-300'
          >
            <Eye className='h-4 w-4' />
            Открыть урок
          </Link>
        )}
      </div>
    </article>
  )
}

function LessonLifecycleLists({ scope, editBaseHref, initialClasses = null, initialClassesPagination = null }: LifecycleListsProps) {
  const [classes, setClasses] = useState<ClassroomItem[]>(initialClasses || [])
  const [classesLoading, setClassesLoading] = useState(scope === 'teacher' && !initialClasses)
  const [classesError, setClassesError] = useState<string | null>(null)
  const [classesReloadToken, setClassesReloadToken] = useState(0)
  const [classesPage, setClassesPage] = useState(initialClassesPagination?.page ?? 1)
  const [classesPagination, setClassesPagination] = useState<PaginationMeta | null>(initialClassesPagination)
  const [selectedClassId, setSelectedClassId] = useState<number | null>(initialClasses?.[0]?.id ?? null)
  const [selectedClassSnapshot, setSelectedClassSnapshot] = useState<ClassroomItem | null>(initialClasses?.[0] ?? null)
  const [drafts, setDrafts] = useState<LessonAuthoringListItem[]>([])
  const [published, setPublished] = useState<LessonAuthoringListItem[]>([])
  const [draftPage, setDraftPage] = useState(1)
  const [publishedPage, setPublishedPage] = useState(1)
  const [draftPagination, setDraftPagination] = useState<PaginationMeta | null>(null)
  const [publishedPagination, setPublishedPagination] = useState<PaginationMeta | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [publishCandidate, setPublishCandidate] = useState<PublishCandidate | null>(null)
  const [publishing, setPublishing] = useState(false)
  const requestId = useRef(0)

  const draftsWindow = useFiveItemWindow({
    items: drafts,
    pagination: draftPagination,
    loading,
    onPageChange: setDraftPage,
    resetKey: selectedClassId,
  })
  const publishedWindow = useFiveItemWindow({
    items: published,
    pagination: publishedPagination,
    loading,
    onPageChange: setPublishedPage,
    resetKey: selectedClassId,
  })

  const selectedClass = useMemo(
    () => classes.find(item => item.id === selectedClassId) || (selectedClassSnapshot?.id === selectedClassId ? selectedClassSnapshot : null),
    [classes, selectedClassId, selectedClassSnapshot],
  )
  const classesWindow = useFiveItemWindow({ items: classes, pagination: classesPagination, loading: classesLoading, onPageChange: setClassesPage })

  useEffect(() => {
    if (scope !== 'teacher' || (initialClasses && classesPage === initialClassesPagination?.page && classesReloadToken === 0)) return
    let cancelled = false
    setClassesLoading(true)
    api<{ classes: ClassroomItem[]; pagination: PaginationMeta }>(`/teacher/classes?page=${classesPage}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required')
      .then(data => {
        if (cancelled) return
        setClasses(data.classes)
        setClassesPagination(data.pagination)
        setSelectedClassId(current => current ?? data.classes[0]?.id ?? null)
        setClassesError(null)
      })
      .catch(loadError => {
        if (!cancelled) setClassesError(getApiErrorMessage(loadError, 'Не удалось загрузить классы.'))
      })
      .finally(() => {
        if (!cancelled) setClassesLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [classesPage, classesReloadToken, initialClasses, initialClassesPagination?.page, scope])

  async function loadLessons(nextDraftPage = draftPage, nextPublishedPage = publishedPage) {
    if (scope === 'teacher' && !selectedClassId) {
      setDrafts([])
      setPublished([])
      setDraftPagination(null)
      setPublishedPagination(null)
      return
    }
    const base = scope === 'teacher'
      ? `/teacher/classes/${selectedClassId}/lessons`
      : '/admin/lessons'
    setLoading(true)
    setError(null)
    const currentRequestId = ++requestId.current
    try {
      const [draftResult, publishedResult] = await Promise.all([
        api<LessonLifecycleListResponse>(`${base}?status=draft&page=${nextDraftPage}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required'),
        api<LessonLifecycleListResponse>(`${base}?status=published&page=${nextPublishedPage}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required'),
      ])
      if (currentRequestId !== requestId.current) return
      setDrafts(draftResult.lessons)
      setPublished(publishedResult.lessons)
      setDraftPagination(draftResult.pagination)
      setPublishedPagination(publishedResult.pagination)
    } catch (loadError) {
      if (currentRequestId !== requestId.current) return
      setError(getApiErrorMessage(loadError, 'Не удалось загрузить сохранённые уроки.'))
      setDrafts([])
      setPublished([])
    } finally {
      if (currentRequestId === requestId.current) setLoading(false)
    }
  }

  useEffect(() => {
    if (scope === 'teacher' && (classesLoading || !selectedClassId)) return
    void loadLessons()
    // The selected class fully determines the teacher endpoint; the admin
    // endpoint has no filter and should load once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classesLoading, draftPage, publishedPage, scope, selectedClassId])

  useEffect(() => {
    setDraftPage(1)
    setPublishedPage(1)
  }, [selectedClassId])

  function requestPublish(lesson: LessonAuthoringListItem) {
    const classroomId = lesson.classroom_id ?? selectedClassId
    if (scope === 'teacher' && !classroomId) {
      showErrorToast('Не удалось определить класс урока. Откройте его для редактирования и попробуйте снова.')
      return
    }
    setPublishCandidate({ lesson, classroomId })
  }

  async function confirmPublish() {
    if (!publishCandidate) return
    const { lesson, classroomId } = publishCandidate
    setPublishing(true)
    try {
      if (scope === 'teacher') {
        await api(
          `/teacher/lessons/${lesson.id}/share`,
          {
            method: 'POST',
            body: JSON.stringify({ classroom_id: classroomId, version: lesson.version }),
          },
          'required',
        )
        showSuccessToast('Урок открыт классу. Ученики получили одно уведомление.')
      } else {
        await api(
          `/admin/lessons/${lesson.id}/publish`,
          { method: 'POST', body: JSON.stringify({ version: lesson.version }) },
          'required',
        )
        showSuccessToast('Урок опубликован.')
      }
      setPublishCandidate(null)
      const nextDraftPage = drafts.length <= 1 && draftPage > 1 ? draftPage - 1 : draftPage
      setDraftPage(nextDraftPage)
      setPublishedPage(1)
      await loadLessons(nextDraftPage, 1)
    } catch (publishError) {
      showErrorToast(getApiErrorMessage(
        publishError,
        'Не удалось опубликовать урок. Проверьте, что черновик заполнен полностью.',
      ))
    } finally {
      setPublishing(false)
    }
  }

  const teacherWithoutClasses = scope === 'teacher' && !classesLoading && classes.length === 0
  const listError = error ? (
    <LessonListEmpty
      title='Уроки не загрузились'
      description={error}
      action={(
        <button
          type='button'
          onClick={() => void loadLessons()}
          className='inline-flex min-h-10 items-center gap-2 rounded-full bg-slate-900 px-4 text-sm font-semibold text-white'
        >
          <RefreshCw className='h-4 w-4' />
          Повторить
        </button>
      )}
    />
  ) : null

  return (
    <section id='lesson-drafts' className='codequest-card scroll-mt-24 p-6 sm:p-7' aria-labelledby='lesson-lifecycle-title'>
      <div className='flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between'>
        <div>
          <p className='brand-eyebrow'>Сохранённые уроки</p>
          <h2 id='lesson-lifecycle-title' className='mt-2 text-2xl font-black text-slate-900'>Черновики и опубликованные уроки</h2>
          <p className='mt-3 max-w-3xl text-sm leading-7 text-slate-600'>
            {scope === 'teacher'
              ? 'Черновик хранится на сервере и доступен только вам. Его можно продолжить с любого устройства; публикация — отдельное действие.'
              : 'Черновик хранится на сервере и доступен сотрудникам с правом редактирования учебной карты. Публикация — отдельное действие.'}
          </p>
        </div>
        <div className='flex flex-wrap items-center gap-2'>
          {scope === 'teacher' ? (
            <label className='min-w-52'>
              <span className='sr-only'>Класс</span>
              <select
                value={selectedClassId ?? ''}
                disabled={classesLoading || !classes.length}
                onChange={event => {
                  const nextId = event.target.value ? Number(event.target.value) : null
                  setSelectedClassId(nextId)
                  setSelectedClassSnapshot(classes.find(item => item.id === nextId) ?? null)
                }}
                className='w-full rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400'
              >
                {classesLoading ? <option>Загружаем классы…</option> : null}
                {!classes.length && !classesLoading ? <option>Нет классов</option> : null}
                {selectedClass && !classesWindow.visibleItems.some(item => item.id === selectedClass.id) ? <option value={selectedClass.id}>{selectedClass.name}</option> : null}
                {classesWindow.visibleItems.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <FiveItemPager window={classesWindow} loading={classesLoading} itemLabel='классов' className='mt-2' />
            </label>
          ) : null}
          {scope === 'teacher' ? (
            <Link
              href={selectedClassId ? `/teacher/lessons/create?classId=${selectedClassId}` : '/teacher/lessons/create'}
              className='inline-flex min-h-10 items-center gap-2 rounded-full bg-sky-600 px-4 text-sm font-semibold text-white transition hover:bg-sky-700'
            >
              <BookOpen className='h-4 w-4' />
              Создать урок
            </Link>
          ) : null}
          <button
            type='button'
            onClick={() => void loadLessons()}
            disabled={loading || classesLoading || teacherWithoutClasses}
            className='inline-flex min-h-10 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-60'
          >
            <RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} />
            Обновить
          </button>
        </div>
      </div>

      {classesError ? (
        <div className='mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800'>
          <span>{classesError}</span>
          <button type='button' onClick={() => setClassesReloadToken(value => value + 1)} className='rounded-full bg-white px-3 py-1.5 text-sm font-semibold text-rose-800'>Повторить</button>
        </div>
      ) : null}

      {teacherWithoutClasses ? (
        <div className='mt-6'>
          <LessonListEmpty
            title='Сначала создайте класс'
            description='Авторские уроки сохраняются в библиотеку конкретного класса.'
            action={<Link href='/teacher' className='inline-flex min-h-10 items-center rounded-full bg-sky-600 px-4 text-sm font-semibold text-white'>Перейти в кабинет</Link>}
          />
        </div>
      ) : (
        <div className='mt-6 grid gap-6 xl:grid-cols-2'>
          <section aria-labelledby='lesson-draft-list-title'>
            <div className='flex flex-wrap items-center justify-between gap-3'>
              <div>
                <h3 id='lesson-draft-list-title' className='text-lg font-bold text-slate-900'>Черновики</h3>
                <p className='mt-1 text-sm text-slate-500'>Ещё не видны ученикам.</p>
              </div>
              <span className='rounded-full bg-amber-100 px-3 py-1.5 text-sm font-bold text-amber-800'>{draftPagination?.total ?? drafts.length}</span>
            </div>
            <div className='mt-4 space-y-3'>
              {loading ? <LessonListEmpty title='Загружаем черновики' description='Проверяем сохранённые уроки.' />
                : listError
                  ? listError
                  : drafts.length
                    ? draftsWindow.visibleItems.map(lesson => <LessonCard key={lesson.id} lesson={lesson} scope={scope} editBaseHref={editBaseHref} onPublish={requestPublish} />)
                    : <LessonListEmpty title='Черновиков пока нет' description='Нажмите «Сохранить черновик» в конструкторе, чтобы вернуться к уроку позже.' />}
            </div>
            <FiveItemPager window={draftsWindow} loading={loading} itemLabel='черновиков' className='mt-4' />
          </section>

          <section aria-labelledby='lesson-published-list-title'>
            <div className='flex flex-wrap items-center justify-between gap-3'>
              <div>
                <h3 id='lesson-published-list-title' className='text-lg font-bold text-slate-900'>Опубликованные</h3>
                <p className='mt-1 text-sm text-slate-500'>Их содержание по-прежнему можно редактировать.</p>
              </div>
              <span className='rounded-full bg-emerald-100 px-3 py-1.5 text-sm font-bold text-emerald-800'>{publishedPagination?.total ?? published.length}</span>
            </div>
            <div className='mt-4 space-y-3'>
              {loading ? <LessonListEmpty title='Загружаем опубликованные уроки' description='Проверяем актуальный список.' />
                : listError
                  ? listError
                  : published.length
                    ? publishedWindow.visibleItems.map(lesson => <LessonCard key={lesson.id} lesson={lesson} scope={scope} editBaseHref={editBaseHref} onPublish={requestPublish} />)
                    : <LessonListEmpty title='Опубликованных уроков пока нет' description='После публикации урок появится здесь и останется доступным для редактирования.' />}
            </div>
            <FiveItemPager window={publishedWindow} loading={loading} itemLabel='уроков' className='mt-4' />
          </section>
        </div>
      )}

      {publishCandidate ? (
        <div className='fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-6 backdrop-blur-sm' role='dialog' aria-modal='true' aria-labelledby='lesson-publish-title'>
          <div className='w-full max-w-lg rounded-[28px] bg-white p-6 shadow-2xl'>
            <div className='flex items-start justify-between gap-4'>
              <div>
                <p className='brand-eyebrow'>Публикация урока</p>
                <h2 id='lesson-publish-title' className='mt-2 text-2xl font-black text-slate-900'>Опубликовать «{publishCandidate.lesson.title || 'урок без названия'}»?</h2>
              </div>
              <button type='button' onClick={() => setPublishCandidate(null)} disabled={publishing} className='inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-600'>
                <X className='h-4 w-4' />
              </button>
            </div>
            <p className='mt-4 text-sm leading-7 text-slate-600'>
              {scope === 'teacher'
                ? `Урок станет виден классу «${selectedClass?.name || publishCandidate.lesson.classroom_name || 'выбранный класс'}», а ученики получат уведомление.`
                : 'Урок станет опубликованным. Если его модуль скрыт, ученики пока не увидят модуль целиком.'}
            </p>
            <div className='mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end'>
              <button type='button' onClick={() => setPublishCandidate(null)} disabled={publishing} className='min-h-11 rounded-full bg-slate-100 px-5 text-sm font-semibold text-slate-700'>Отмена</button>
              <button type='button' onClick={() => void confirmPublish()} disabled={publishing} className='min-h-11 rounded-full bg-sky-600 px-5 text-sm font-semibold text-white disabled:opacity-60'>
                {publishing ? 'Публикуем…' : scope === 'teacher' ? 'Открыть классу' : 'Опубликовать'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}

export function AdminLessonLifecycleLists({ editBaseHref }: { editBaseHref: string }) {
  return <LessonLifecycleLists scope='admin' editBaseHref={editBaseHref} />
}

export function TeacherLessonLifecycleLists({ initialClasses, initialClassesPagination }: { initialClasses?: ClassroomItem[] | null; initialClassesPagination?: PaginationMeta | null }) {
  return <LessonLifecycleLists scope='teacher' editBaseHref='/teacher/lessons' initialClasses={initialClasses} initialClassesPagination={initialClassesPagination} />
}
