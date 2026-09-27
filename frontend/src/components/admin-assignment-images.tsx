'use client'

// Admin-only screen to upload assignment cover images and attach them to existing
// assignments. Intentionally minimal: list -> upload -> attach. Full assignment
// management (filtering, search, multi-select) lives elsewhere; this is just the
// media surface so admins can replace auto-generated SVG placeholders with curated art.

import { useCallback, useEffect, useMemo, useState } from 'react'

import { api, getApiErrorMessage } from '@/lib/api'
import { FiveItemPager, SERVER_PAGE_SIZE, useFiveItemWindow } from '@/components/five-item-navigator'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import type { PaginationMeta } from '@/types'

type MediaImage = {
  id: number
  kind: string
  format: string
  width: number | null
  height: number | null
  byte_size: number
  sha256: string
  is_generated: boolean
  url: string
  created_at: string | null
}

type AssignmentRow = {
  id: number
  title: string
  classroom_name: string | null
  image_id: number | null
  image_url: string | null
}

type ImageList = { images: MediaImage[]; pagination: PaginationMeta }

type AssignmentList = { assignments: AssignmentRow[]; pagination: PaginationMeta }

const MAX_UPLOAD_BYTES = 5 * 1024 * 1024

export function AdminAssignmentImages() {
  const [images, setImages] = useState<MediaImage[]>([])
  const [assignments, setAssignments] = useState<AssignmentRow[]>([])
  const [uploadBusy, setUploadBusy] = useState(false)
  const [attachBusyId, setAttachBusyId] = useState<number | null>(null)
  const [loadErr, setLoadErr] = useState('')
  const [imagesPage, setImagesPage] = useState(1)
  const [assignmentsPage, setAssignmentsPage] = useState(1)
  const [imagesPagination, setImagesPagination] = useState<PaginationMeta | null>(null)
  const [assignmentsPagination, setAssignmentsPagination] = useState<PaginationMeta | null>(null)
  const [loadingImages, setLoadingImages] = useState(false)
  const [loadingAssignments, setLoadingAssignments] = useState(false)
  const imagesWindow = useFiveItemWindow({ items: images, pagination: imagesPagination, loading: loadingImages, onPageChange: setImagesPage })
  const assignmentsWindow = useFiveItemWindow({ items: assignments, pagination: assignmentsPagination, loading: loadingAssignments, onPageChange: setAssignmentsPage })

  const refreshImages = useCallback(async (page = imagesPage) => {
    setLoadingImages(true)
    try {
      const data = await api<ImageList>(`/admin/media/images?page=${page}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required')
      setImages(data.images || [])
      setImagesPagination(data.pagination)
    } catch (e) {
      setLoadErr(getApiErrorMessage(e, 'Не удалось загрузить список изображений.'))
    } finally { setLoadingImages(false) }
  }, [imagesPage])

  const refreshAssignments = useCallback(async (page = assignmentsPage) => {
    setLoadingAssignments(true)
    try {
      // Re-uses the existing admin overview wiring: assignments are exposed via
      // /api/admin/assignments-light (not yet implemented) -> fallback to /api/admin/overview
      // that returns counts only. To keep this PR focused, we expose a simple list endpoint.
      const data = await api<AssignmentList>(`/admin/assignments-light?page=${page}&page_size=${SERVER_PAGE_SIZE}`, undefined, 'required')
      setAssignments(data.assignments || [])
      setAssignmentsPagination(data.pagination)
    } catch (e) {
      setLoadErr(getApiErrorMessage(e, 'Не удалось загрузить список заданий.'))
    } finally { setLoadingAssignments(false) }
  }, [assignmentsPage])

  useEffect(() => {
    void refreshImages()
    void refreshAssignments()
  }, [refreshImages, refreshAssignments])

  const onUpload = useCallback(
    async (file: File) => {
      if (file.size > MAX_UPLOAD_BYTES) {
        showErrorToast('Файл больше 5 МБ.')
        return
      }
      setUploadBusy(true)
      try {
        const form = new FormData()
        form.append('file', file)
        await api('/admin/media/images', { method: 'POST', body: form }, 'required')
        showSuccessToast('Изображение загружено.')
        await refreshImages()
      } catch (e) {
        showErrorToast(getApiErrorMessage(e, 'Не удалось загрузить изображение.'))
      } finally {
        setUploadBusy(false)
      }
    },
    [refreshImages],
  )

  const onAttach = useCallback(
    async (assignmentId: number, imageId: number | null) => {
      setAttachBusyId(assignmentId)
      try {
        await api(
          `/admin/assignments/${assignmentId}/image`,
          { method: 'PATCH', body: JSON.stringify({ image_id: imageId }) },
          'required',
        )
        showSuccessToast(imageId ? 'Картинка прикреплена.' : 'Картинка отвязана.')
        await refreshAssignments()
      } catch (e) {
        showErrorToast(getApiErrorMessage(e, 'Не удалось обновить задание.'))
      } finally {
        setAttachBusyId(null)
      }
    },
    [refreshAssignments],
  )

  const imagesById = useMemo(() => {
    const map = new Map<number, MediaImage>()
    for (const image of images) map.set(image.id, image)
    return map
  }, [images])

  return (
    <main className="page-shell mx-auto w-full max-w-[80rem] space-y-6 py-6">
      <header className="codequest-card p-5 sm:p-6">
        <p className="brand-eyebrow">Медиа</p>
        <h1 className="mt-2 text-2xl font-black text-slate-900">Картинки заданий</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Загрузите PNG/JPEG/WEBP до 5 МБ. Сервер автоматически перекодирует в WebP и удалит метаданные.
          После загрузки прикрепите картинку к нужному заданию.
        </p>
      </header>

      {loadErr ? (
        <div className="codequest-card border border-rose-200 p-4 text-rose-800">{loadErr}</div>
      ) : null}

      <section className="codequest-card p-5 sm:p-6">
        <p className="brand-eyebrow">Загрузка</p>
        <h2 className="mt-2 text-lg font-black text-slate-900">Новое изображение</h2>
        <label className="mt-4 inline-flex cursor-pointer items-center gap-2 brand-button-primary">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={uploadBusy}
            onChange={event => {
              const file = event.target.files?.[0]
              if (file) void onUpload(file)
              event.target.value = ''
            }}
            className="hidden"
          />
          {uploadBusy ? 'Загружаем…' : 'Выбрать файл'}
        </label>

        <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {imagesWindow.visibleItems.map(image => (
            <li
              key={image.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={image.url} alt="" className="h-32 w-full object-cover" />
              <div className="p-3 text-xs">
                <p className="font-semibold text-slate-900">
                  #{image.id} · {image.format.toUpperCase()}
                  {image.is_generated ? ' · авто' : ''}
                </p>
                <p className="mt-1 text-slate-500">
                  {image.width || '?'}×{image.height || '?'} · {Math.ceil(image.byte_size / 1024)} КБ
                </p>
              </div>
            </li>
          ))}
          {images.length === 0 ? (
            <li className="text-sm text-slate-500">Пока нет загруженных изображений.</li>
          ) : null}
        </ul>
        <FiveItemPager window={imagesWindow} loading={loadingImages} itemLabel='изображений' className='mt-4' />
      </section>

      <section className="codequest-card p-5 sm:p-6">
        <p className="brand-eyebrow">Привязка</p>
        <h2 className="mt-2 text-lg font-black text-slate-900">Задания и обложки</h2>
        <ul className="mt-5 space-y-3">
          {assignmentsWindow.visibleItems.map(assignment => {
            const currentImage = assignment.image_id != null ? imagesById.get(assignment.image_id) ?? null : null
            return (
              <li
                key={assignment.id}
                className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center"
              >
                <div className="flex min-w-0 items-center gap-3">
                  {assignment.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={assignment.image_url}
                      alt=""
                      className="h-14 w-20 shrink-0 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="h-14 w-20 shrink-0 rounded-lg border border-dashed border-slate-300 text-center text-xs leading-[3.5rem] text-slate-400">
                      нет
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-900">{assignment.title}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{assignment.classroom_name || '—'}</p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <select
                    value={assignment.image_id ?? ''}
                    onChange={event => {
                      const next = event.target.value
                      void onAttach(assignment.id, next ? Number(next) : null)
                    }}
                    disabled={attachBusyId === assignment.id}
                    className="rounded-full border border-slate-200 px-3 py-1.5 text-sm"
                  >
                    <option value="">— без картинки —</option>
                    {assignment.image_id != null && !imagesWindow.visibleItems.some(image => image.id === assignment.image_id) ? <option value={assignment.image_id}>#{assignment.image_id} (текущая)</option> : null}
                    {imagesWindow.visibleItems.map(image => (
                      <option key={image.id} value={image.id}>
                        #{image.id} {image.is_generated ? '(авто)' : ''}
                      </option>
                    ))}
                  </select>
                  {currentImage && currentImage.is_generated ? (
                    <span className="text-xs text-slate-400">авто-плейсхолдер</span>
                  ) : null}
                </div>
              </li>
            )
          })}
          {assignments.length === 0 ? (
            <li className="text-sm text-slate-500">Заданий пока нет.</li>
          ) : null}
        </ul>
        <FiveItemPager window={assignmentsWindow} loading={loadingAssignments} itemLabel='заданий' className='mt-4' />
      </section>
    </main>
  )
}
