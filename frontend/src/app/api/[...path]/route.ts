import { NextRequest, NextResponse } from 'next/server'

import { getInternalApiUrl } from '@/lib/server-env'
import {
  DEFAULT_SERVER_REQUEST_TIMEOUT_MS,
  isRequestTimeoutError,
  UPLOAD_BROWSER_REQUEST_TIMEOUT_MS,
  withRequestTimeout,
} from '@/lib/request-timeout'
import { trustedClientIp } from '@/lib/trusted-client-ip'

/** Must match backend `CSRF_COOKIE_NAME` / `CSRF_HEADER_NAME` (cookie + header double-submit). */
const FORWARDED_COOKIE_NAMES = [
  'codequest_access_token',
  'codequest_refresh_token',
  'csrf_token',
] as const
const CSRF_HEADER = 'X-CSRF-Token'
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const DEFAULT_MAX_REQUEST_BODY_BYTES = 8 * 1024 * 1024

export const dynamic = 'force-dynamic'

function backendUrl(path: string, search: string) {
  return `${getInternalApiUrl()}/${path}${search}`
}

function positiveIntegerSetting(name: string, fallback: number) {
  const parsed = Number(process.env[name])
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback
}

function maxRequestBodyBytes() {
  return positiveIntegerSetting('BFF_MAX_REQUEST_BODY_BYTES', DEFAULT_MAX_REQUEST_BODY_BYTES)
}

class RequestBodyTooLargeError extends Error {}

async function readBoundedRequestBody(request: NextRequest): Promise<ArrayBuffer | undefined> {
  if (request.method === 'GET' || request.method === 'HEAD' || !request.body) {
    return undefined
  }

  const limit = maxRequestBodyBytes()
  const declaredLength = Number(request.headers.get('content-length'))
  if (Number.isFinite(declaredLength) && declaredLength > limit) {
    throw new RequestBodyTooLargeError()
  }

  const reader = request.body.getReader()
  const chunks: Uint8Array[] = []
  let total = 0

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      total += value.byteLength
      if (total > limit) {
        await reader.cancel('request body limit exceeded')
        throw new RequestBodyTooLargeError()
      }
      chunks.push(value)
    }
  } finally {
    reader.releaseLock()
  }

  if (total === 0) return undefined
  const body = new Uint8Array(total)
  let offset = 0
  for (const chunk of chunks) {
    body.set(chunk, offset)
    offset += chunk.byteLength
  }
  return body.buffer
}

function proxiedCookieHeader(request: NextRequest) {
  const parts = FORWARDED_COOKIE_NAMES.map((name) => {
    const value = request.cookies.get(name)?.value
    return value ? `${name}=${encodeURIComponent(value)}` : ''
  }).filter(Boolean)
  return parts.join('; ')
}

function responseCookieHeaders(response: Response) {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[]
  }
  if (typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie()
  }
  const fallback = response.headers.get('set-cookie')
  return fallback ? [fallback] : []
}

async function forwardRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params
  const upstreamHeaders = new Headers()
  const cookieHeader = proxiedCookieHeader(request)
  const contentType = request.headers.get('content-type')
  const accept = request.headers.get('accept')
  const authorization = request.headers.get('authorization')
  const origin = request.headers.get('origin')?.trim()
  const clientIp = trustedClientIp(request.headers)

  if (cookieHeader) {
    upstreamHeaders.set('cookie', cookieHeader)
  }
  if (contentType) {
    upstreamHeaders.set('content-type', contentType)
  }
  if (accept) {
    upstreamHeaders.set('accept', accept)
  }
  if (authorization) {
    upstreamHeaders.set('authorization', authorization)
  }
  if (clientIp) {
    // Backend trusts exactly one proxy hop. Send one validated address, never
    // the browser-controlled X-Forwarded-For/X-Real-IP headers.
    upstreamHeaders.set('x-forwarded-for', clientIp)
  }

  const method = request.method.toUpperCase()
  if (UNSAFE_METHODS.has(method)) {
    const csrfFromClient = request.headers.get(CSRF_HEADER)?.trim()
    if (origin) {
      upstreamHeaders.set('origin', origin)
    }
    if (csrfFromClient) {
      upstreamHeaders.set(CSRF_HEADER, csrfFromClient)
    }
  }

  let body: ArrayBuffer | undefined
  try {
    body = await readBoundedRequestBody(request)
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return NextResponse.json(
        { message: 'Размер запроса превышает допустимый лимит.', code: 'request_too_large' },
        { status: 413 },
      )
    }
    throw error
  }

  let upstreamResponse: Response
  try {
    upstreamResponse = await withRequestTimeout(
      signal => fetch(
        backendUrl(path.join('/'), request.nextUrl.search),
        {
          method: request.method,
          headers: upstreamHeaders,
          body,
          cache: 'no-store',
          redirect: 'manual',
          signal,
        },
      ),
      body ? UPLOAD_BROWSER_REQUEST_TIMEOUT_MS : DEFAULT_SERVER_REQUEST_TIMEOUT_MS,
      request.signal,
    )
  } catch (error) {
    if (isRequestTimeoutError(error)) {
      return NextResponse.json(
        { message: 'Внутренний сервис не ответил вовремя.', code: 'upstream_timeout' },
        { status: 504 },
      )
    }
    return NextResponse.json(
      { message: 'Внутренний сервис временно недоступен.', code: 'upstream_unavailable' },
      { status: 502 },
    )
  }

  const responseHeaders = new Headers()
  for (const headerName of ['cache-control', 'content-type', 'etag', 'last-modified', 'vary']) {
    const value = upstreamResponse.headers.get(headerName)
    if (value) {
      responseHeaders.set(headerName, value)
    }
  }

  const response = new NextResponse(upstreamResponse.body, {
    status: upstreamResponse.status,
    headers: responseHeaders,
  })
  for (const cookie of responseCookieHeaders(upstreamResponse)) {
    response.headers.append('set-cookie', cookie)
  }
  return response
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forwardRequest(request, context)
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forwardRequest(request, context)
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forwardRequest(request, context)
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forwardRequest(request, context)
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forwardRequest(request, context)
}

export async function OPTIONS(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forwardRequest(request, context)
}
