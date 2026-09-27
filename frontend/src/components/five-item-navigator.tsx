'use client'

import { ChevronLeft, ChevronRight, LoaderCircle } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { PaginationMeta } from '@/types'

export const SERVER_PAGE_SIZE = 15
export const FIVE_ITEM_WINDOW_SIZE = 5

export function clampPageToPagination(requestedPage: number, pagination?: PaginationMeta | null) {
  if (!pagination) return Math.max(1, requestedPage)
  return Math.min(Math.max(1, requestedPage), Math.max(1, pagination.total_pages))
}

interface FiveItemWindowOptions<T> {
  items: T[]
  pagination?: PaginationMeta | null
  loading?: boolean
  onPageChange?: (page: number) => void | Promise<void>
  /** Change this when filters or the surrounding collection change. */
  resetKey?: string | number | null
}

export function useFiveItemWindow<T>({
  items,
  pagination,
  loading = false,
  onPageChange,
  resetKey,
}: FiveItemWindowOptions<T>) {
  const [windowIndex, setWindowIndex] = useState(0)
  const pendingDirection = useRef<'previous' | 'next' | null>(null)
  const previousServerPage = useRef(pagination?.page ?? 1)
  const lastResetKey = useRef(resetKey)

  const windowCount = Math.max(1, Math.ceil(items.length / FIVE_ITEM_WINDOW_SIZE))
  const visibleItems = useMemo(
    () => items.slice(
      windowIndex * FIVE_ITEM_WINDOW_SIZE,
      (windowIndex + 1) * FIVE_ITEM_WINDOW_SIZE,
    ),
    [items, windowIndex],
  )

  useEffect(() => {
    if (Object.is(lastResetKey.current, resetKey)) return
    lastResetKey.current = resetKey
    pendingDirection.current = null
    setWindowIndex(0)
  }, [resetKey])

  useEffect(() => {
    const serverPage = pagination?.page ?? 1
    if (serverPage !== previousServerPage.current) {
      setWindowIndex(pendingDirection.current === 'previous' ? windowCount - 1 : 0)
      previousServerPage.current = serverPage
      pendingDirection.current = null
      return
    }
    setWindowIndex(current => Math.min(current, windowCount - 1))
  }, [pagination?.page, windowCount])

  const canPrevious = windowIndex > 0 || (pagination?.page ?? 1) > 1
  const canNext = windowIndex < windowCount - 1
    || (pagination ? pagination.page < pagination.total_pages : false)

  const movePrevious = useCallback(() => {
    if (loading || !canPrevious) return
    if (windowIndex > 0) {
      setWindowIndex(current => Math.max(0, current - 1))
      return
    }
    if (pagination && onPageChange) {
      pendingDirection.current = 'previous'
      void onPageChange(pagination.page - 1)
    }
  }, [canPrevious, loading, onPageChange, pagination, windowIndex])

  const moveNext = useCallback(() => {
    if (loading || !canNext) return
    if (windowIndex < windowCount - 1) {
      setWindowIndex(current => Math.min(windowCount - 1, current + 1))
      return
    }
    if (pagination && onPageChange) {
      pendingDirection.current = 'next'
      void onPageChange(pagination.page + 1)
    }
  }, [canNext, loading, onPageChange, pagination, windowCount, windowIndex])

  const firstItem = items.length ? ((pagination?.page ?? 1) - 1) * (pagination?.page_size ?? SERVER_PAGE_SIZE)
    + windowIndex * FIVE_ITEM_WINDOW_SIZE + 1 : 0
  const lastItem = items.length
    ? Math.min(firstItem + visibleItems.length - 1, pagination?.total ?? items.length)
    : 0
  const total = pagination?.total ?? items.length

  return {
    visibleItems,
    canPrevious,
    canNext,
    movePrevious,
    moveNext,
    firstItem,
    lastItem,
    total,
  }
}

interface FiveItemNavigatorProps {
  canPrevious: boolean
  canNext: boolean
  onPrevious: () => void
  onNext: () => void
  loading?: boolean
  firstItem: number
  lastItem: number
  total: number
  itemLabel?: string
  className?: string
}

export function FiveItemNavigator({
  canPrevious,
  canNext,
  onPrevious,
  onNext,
  loading = false,
  firstItem,
  lastItem,
  total,
  itemLabel = 'объектов',
  className = '',
}: FiveItemNavigatorProps) {
  if (!total) return null

  return (
    <nav
      className={`flex flex-wrap items-center justify-between gap-3 ${className}`}
      aria-label={`Навигация по списку ${itemLabel}`}
    >
      <p className='text-xs font-semibold text-slate-500' aria-live='polite'>
        {firstItem}–{lastItem} из {total}
      </p>
      <div className='flex items-center gap-2'>
        <button
          type='button'
          onClick={onPrevious}
          disabled={loading || !canPrevious}
          aria-label={`Показать предыдущие ${FIVE_ITEM_WINDOW_SIZE} ${itemLabel}`}
          title={`Предыдущие ${FIVE_ITEM_WINDOW_SIZE}`}
          className='inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-sky-300 hover:text-sky-700 disabled:cursor-not-allowed disabled:opacity-40'
        >
          {loading ? <LoaderCircle className='h-4 w-4 animate-spin' aria-hidden='true' /> : <ChevronLeft className='h-5 w-5' aria-hidden='true' />}
        </button>
        <button
          type='button'
          onClick={onNext}
          disabled={loading || !canNext}
          aria-label={`Показать следующие ${FIVE_ITEM_WINDOW_SIZE} ${itemLabel}`}
          title={`Следующие ${FIVE_ITEM_WINDOW_SIZE}`}
          className='inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 transition hover:border-sky-300 hover:text-sky-700 disabled:cursor-not-allowed disabled:opacity-40'
        >
          {loading ? <LoaderCircle className='h-4 w-4 animate-spin' aria-hidden='true' /> : <ChevronRight className='h-5 w-5' aria-hidden='true' />}
        </button>
      </div>
    </nav>
  )
}

export function FiveItemPager({
  window,
  loading,
  itemLabel,
  className,
}: {
  window: ReturnType<typeof useFiveItemWindow<unknown>>
  loading?: boolean
  itemLabel?: string
  className?: string
}) {
  return (
    <FiveItemNavigator
      canPrevious={window.canPrevious}
      canNext={window.canNext}
      onPrevious={window.movePrevious}
      onNext={window.moveNext}
      loading={loading}
      firstItem={window.firstItem}
      lastItem={window.lastItem}
      total={window.total}
      itemLabel={itemLabel}
      className={className}
    />
  )
}
