import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

import type { LessonPlayerPayload } from '@/components/lesson-player-helpers'
import { getInternalApiUrl } from '@/lib/server-env'
import {
  DEFAULT_SERVER_REQUEST_TIMEOUT_MS,
  UPLOAD_BROWSER_REQUEST_TIMEOUT_MS,
  withRequestTimeout,
} from '@/lib/request-timeout'
import {
  redirectForServerStatus,
  ServerApiResponseError,
} from '@/lib/server-response-policy'

const FORWARDED_COOKIE_NAMES = [
  'codequest_access_token',
  'codequest_refresh_token',
  'csrf_token',
] as const
const CSRF_HEADER = 'X-CSRF-Token'

function normalizePath(path: string) {
  return path.startsWith('/') ? path : `/${path}`
}

function extractMessage(payload: unknown) {
  if (!payload || typeof payload !== 'object' || !('message' in payload)) {
    return null
  }
  return typeof payload.message === 'string' ? payload.message : null
}

function enforceRouteResponse(response: Response, payload: unknown): asserts response is Response {
  if (response.ok) return
  const destination = redirectForServerStatus(response.status)
  if (destination) redirect(destination)
  throw new ServerApiResponseError(
    response.status,
    extractMessage(payload) || `Server request failed with status ${response.status}`,
    payload,
  )
}

function serverRequestTimeoutMs(init?: RequestInit) {
  return typeof FormData !== 'undefined' && init?.body instanceof FormData
    ? UPLOAD_BROWSER_REQUEST_TIMEOUT_MS
    : DEFAULT_SERVER_REQUEST_TIMEOUT_MS
}

/**
 * Первичная загрузка урока: при 404 с бэкенда — сигнал для notFound() (без HTML в React).
 */
export async function fetchLessonPlayerInitial(lessonId: string): Promise<LessonPlayerPayload | 'not_found'> {
  const cookieStore = await cookies()
  const cookieHeader = FORWARDED_COOKIE_NAMES.map((name) => {
    const value = cookieStore.get(name)?.value
    return value ? `${name}=${encodeURIComponent(value)}` : ''
  })
    .filter(Boolean)
    .join('; ')

  const path = normalizePath(`/lessons/${encodeURIComponent(lessonId)}`)
  const { response, text } = await withRequestTimeout(async signal => {
    const response = await fetch(`${getInternalApiUrl()}${path}`, {
      method: 'GET',
      headers: {
        accept: 'application/json',
        ...(cookieHeader ? { cookie: cookieHeader } : {}),
      },
      cache: 'no-store',
      signal,
    })
    return { response, text: await response.text() }
  }, DEFAULT_SERVER_REQUEST_TIMEOUT_MS)
  if (response.status === 404) {
    return 'not_found'
  }
  let payload: unknown = null
  try {
    payload = text ? JSON.parse(text) as unknown : null
  } catch {
    payload = null
  }
  enforceRouteResponse(response, payload)
  if (!payload || typeof payload !== 'object') {
    throw new ServerApiResponseError(response.status, 'Lesson response was not valid JSON', payload)
  }
  return payload as LessonPlayerPayload
}

export async function serverApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const cookieStore = await cookies()
  const cookieHeader = FORWARDED_COOKIE_NAMES.map((name) => {
    const value = cookieStore.get(name)?.value
    return value ? `${name}=${encodeURIComponent(value)}` : ''
  })
    .filter(Boolean)
    .join('; ')

  const method = (init.method || 'GET').toUpperCase()
  const csrf = cookieStore.get('csrf_token')?.value?.trim()
  const needsCsrfHeader = !['GET', 'HEAD', 'OPTIONS'].includes(method)

  const { response, text } = await withRequestTimeout(async signal => {
    const response = await fetch(`${getInternalApiUrl()}${normalizePath(path)}`, {
      ...init,
      headers: {
        accept: 'application/json',
        ...(init.headers || {}),
        ...(cookieHeader ? { cookie: cookieHeader } : {}),
        ...(needsCsrfHeader && csrf ? { [CSRF_HEADER]: csrf } : {}),
      },
      cache: 'no-store',
      signal,
    })
    return { response, text: await response.text() }
  }, serverRequestTimeoutMs(init), init.signal)
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text) as unknown
    } catch {
      payload = null
    }
  }
  enforceRouteResponse(response, payload)
  return payload as T
}
