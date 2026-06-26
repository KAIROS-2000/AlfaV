import { NextRequest, NextResponse } from 'next/server'

import { INTERNAL_API_URL } from '@/lib/server-env'

/** Must match backend `CSRF_COOKIE_NAME` / `CSRF_HEADER_NAME` (cookie + header double-submit). */
const FORWARDED_COOKIE_NAMES = [
  'codequest_access_token',
  'codequest_refresh_token',
  'csrf_token',
] as const
const CSRF_HEADER = 'X-CSRF-Token'
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export const dynamic = 'force-dynamic'

function backendUrl(path: string, search: string) {
  return `${INTERNAL_API_URL}/${path}${search}`
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

  const method = request.method.toUpperCase()
  if (UNSAFE_METHODS.has(method)) {
    // Forward the client's Origin VERBATIM (no fallback to a trusted origin):
    // a real browser always sends it, and the backend allow-list rejects a
    // foreign one. Falling back to the app's own origin when it's absent would
    // let a cross-site request with no Origin borrow a trusted value and pass
    // the backend check. And forward ONLY the client-supplied CSRF header —
    // deriving it from the csrf_token cookie here would defeat the backend's
    // double-submit check (the browser client now sends X-CSRF-Token itself).
    const clientOrigin = request.headers.get('origin')?.trim()
    if (clientOrigin) {
      upstreamHeaders.set('origin', clientOrigin)
    }
    const csrf = request.headers.get(CSRF_HEADER)?.trim()
    if (csrf) {
      upstreamHeaders.set(CSRF_HEADER, csrf)
    }
  }

  const body =
    request.method === 'GET' || request.method === 'HEAD'
      ? undefined
      : await request.arrayBuffer()

  const upstreamResponse = await fetch(
    backendUrl(path.join('/'), request.nextUrl.search),
    {
      method: request.method,
      headers: upstreamHeaders,
      body: body && body.byteLength > 0 ? body : undefined,
      cache: 'no-store',
      redirect: 'manual',
    },
  )

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
