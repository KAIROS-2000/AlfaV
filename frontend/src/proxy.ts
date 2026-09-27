import { NextRequest, NextResponse } from 'next/server'

import { AUTH_ROUTE_PREFIXES, pathMatches } from '@/lib/auth-routes'
import { getInternalApiBaseUrl } from '@/lib/internal-api-base'
import {
	isKnownRole,
	homePathForRole,
	roleRuleForPath,
	type UserRole,
} from '@/lib/route-access'
import {
	AUTH_SERVER_REQUEST_TIMEOUT_MS,
	withRequestTimeout,
} from '@/lib/request-timeout'

function buildContentSecurityPolicy() {
	const nonce = crypto.randomUUID().replace(/-/g, '')

	const scriptSrc =
		process.env.NODE_ENV !== 'production'
			? `'self' 'nonce-${nonce}' 'strict-dynamic' 'unsafe-eval'`
			: `'self' 'nonce-${nonce}' 'strict-dynamic'`

	const csp = [
		"default-src 'self'",
		`script-src ${scriptSrc}`,
		// No nonce on style-src: with a nonce present, browsers ignore 'unsafe-inline', which blocks
		// React style={{}} and other legitimate inline styles. Script nonce remains for script-src.
		"style-src 'self' 'unsafe-inline'",
		"img-src 'self' data: blob: https://downloader.disk.yandex.ru",
		"font-src 'self' data:",
		"connect-src 'self'",
		"worker-src 'self' blob:",
		"object-src 'none'",
		"base-uri 'none'",
		"form-action 'self'",
		"frame-ancestors 'none'",
		...(process.env.NODE_ENV === 'production' ? ['upgrade-insecure-requests'] : []),
	].join('; ')

	return { nonce, csp }
}

function requestHeadersWithNonce(request: NextRequest, nonce: string) {
	const requestHeaders = new Headers(request.headers)
	requestHeaders.set('x-nonce', nonce)
	return requestHeaders
}

function withCsp(response: NextResponse, csp: string) {
	response.headers.set('Content-Security-Policy', csp)
	return response
}

const ACCESS_COOKIE = 'codequest_access_token'
const REFRESH_COOKIE = 'codequest_refresh_token'
const ACCESS_EXPIRES_AT_COOKIE = 'codequest_access_expires_at'
const CSRF_COOKIE = 'csrf_token'
const CSRF_HEADER = 'X-CSRF-Token'
function loginUrl(request: NextRequest) {
	return new URL('/auth/login', request.url)
}

function dashboardUrl(request: NextRequest, role: UserRole) {
	return new URL(homePathForRole(role), request.url)
}

function authCookieHeader(request: NextRequest) {
	const parts = [ACCESS_COOKIE, REFRESH_COOKIE]
		.map((name) => {
			const value = request.cookies.get(name)?.value
			return value ? `${name}=${encodeURIComponent(value)}` : ''
		})
		.filter(Boolean)
	const csrf = request.cookies.get(CSRF_COOKIE)?.value
	if (csrf) {
		parts.push(`${CSRF_COOKIE}=${encodeURIComponent(csrf)}`)
	}
	return parts.join('; ')
}

function requestOrigin(request: NextRequest) {
	return request.headers.get('origin')?.trim() || request.nextUrl.origin
}

function clearAuthCookies(response: NextResponse) {
	response.cookies.delete(ACCESS_COOKIE)
	response.cookies.delete(REFRESH_COOKIE)
	response.cookies.delete(ACCESS_EXPIRES_AT_COOKIE)
	return response
}

function upstreamSetCookies(response: Response) {
	const headers = response.headers as Headers & {
		getSetCookie?: () => string[]
	}
	if (typeof headers.getSetCookie === 'function') {
		return headers.getSetCookie()
	}
	const fallback = response.headers.get('set-cookie')
	return fallback ? [fallback] : []
}

function requestCookieHeaderWithUpstream(request: NextRequest, upstream: Response) {
	const values = new Map(request.cookies.getAll().map(cookie => [cookie.name, cookie.value]))
	for (const setCookie of upstreamSetCookies(upstream)) {
		const assignment = setCookie.split(';', 1)[0]
		const separator = assignment.indexOf('=')
		if (separator <= 0) continue
		const name = assignment.slice(0, separator).trim()
		const value = assignment.slice(separator + 1).trim()
		if (/max-age=0/i.test(setCookie) || !value) {
			values.delete(name)
		} else {
			values.set(name, value)
		}
	}
	return Array.from(values, ([name, value]) => `${name}=${value}`).join('; ')
}

function applyUpstreamAuthCookies(target: NextResponse, upstream: Response) {
	for (const cookie of upstreamSetCookies(upstream)) {
		target.headers.append('set-cookie', cookie)
	}
	return target
}

type SessionValidation =
	| { status: 'valid'; role: UserRole }
	| { status: 'invalid' }
	| { status: 'unavailable' }

async function validateAccessSession(request: NextRequest): Promise<SessionValidation> {
	if (!request.cookies.get(ACCESS_COOKIE)?.value?.trim()) {
		return { status: 'invalid' }
	}

	try {
		return await withRequestTimeout(async signal => {
			const response = await fetch(`${getInternalApiBaseUrl()}/auth/me`, {
				method: 'GET',
				headers: {
					accept: 'application/json',
					cookie: authCookieHeader(request),
				},
				cache: 'no-store',
				signal,
			})
			const data = (await response.json().catch(() => ({}))) as {
				user?: { role?: string }
			}
			if (response.ok && isKnownRole(data.user?.role)) {
				return { status: 'valid', role: data.user.role }
			}
			if (response.status === 401 || response.status === 403) {
				return { status: 'invalid' }
			}
			return { status: 'unavailable' }
		}, AUTH_SERVER_REQUEST_TIMEOUT_MS, request.signal)
	} catch {
		return { status: 'unavailable' }
	}
}

type LessonAccessPayload = {
	allowed?: boolean
	redirect_lesson_id?: number | null
}

async function forcedSequenceLessonGateResponse(
	request: NextRequest,
	role: UserRole | null,
	csp: string,
	refreshUpstream: Response | null,
	cookieHeader?: string,
): Promise<NextResponse | null> {
	if (role !== 'student' && role !== 'parent') {
		return null
	}
	const match = request.nextUrl.pathname.match(/^\/lessons\/(\d+)\/?$/)
	if (!match) {
		return null
	}
	const lessonId = match[1]
	try {
		const accessResponse = await withRequestTimeout(signal => fetch(
			`${getInternalApiBaseUrl()}/student/lesson-access/${encodeURIComponent(lessonId)}`,
			{
				method: 'GET',
				headers: {
					accept: 'application/json',
					cookie: cookieHeader || authCookieHeader(request),
				},
				cache: 'no-store',
				signal,
			},
		), AUTH_SERVER_REQUEST_TIMEOUT_MS, request.signal)
		if (!accessResponse.ok) {
			return null
		}
		const data = (await accessResponse.json()) as LessonAccessPayload
		if (data.allowed !== false) {
			return null
		}
		const targetId = data.redirect_lesson_id
		const dest =
			targetId != null && String(targetId) !== lessonId
				? new URL(`/lessons/${targetId}`, request.url)
				: new URL('/roadmap', request.url)
		let redirect = NextResponse.redirect(dest)
		if (refreshUpstream) {
			redirect = applyUpstreamAuthCookies(redirect, refreshUpstream)
		}
		return withCsp(redirect, csp)
	} catch {
		return null
	}
}

type RefreshSessionResult =
	| { status: 'valid'; role: UserRole; response: Response }
	| { status: 'invalid' }
	| { status: 'unavailable' }

async function refreshSession(request: NextRequest): Promise<RefreshSessionResult> {
	const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value
	if (!refreshToken) return { status: 'invalid' }

	try {
		const csrf = request.cookies.get(CSRF_COOKIE)?.value?.trim()
		return await withRequestTimeout(async signal => {
			const response = await fetch(`${getInternalApiBaseUrl()}/auth/refresh`, {
				method: 'POST',
				headers: {
					accept: 'application/json',
					cookie: authCookieHeader(request),
					origin: requestOrigin(request),
					...(csrf ? { [CSRF_HEADER]: csrf } : {}),
				},
				cache: 'no-store',
				signal,
			})
			const data = (await response.json().catch(() => ({}))) as {
				user?: { role?: string }
			}
			if (response.ok && isKnownRole(data.user?.role)) {
				return { status: 'valid', role: data.user.role, response }
			}
			if (response.status === 400 || response.status === 401 || response.status === 403) {
				return { status: 'invalid' }
			}
			return { status: 'unavailable' }
		}, AUTH_SERVER_REQUEST_TIMEOUT_MS, request.signal)
	} catch {
		return { status: 'unavailable' }
	}
}

export async function proxy(request: NextRequest) {
	const { nonce, csp } = buildContentSecurityPolicy()
	const requestHeaders = requestHeadersWithNonce(request, nonce)

	const pathname = request.nextUrl.pathname
	const isAuthRoute = AUTH_ROUTE_PREFIXES.some((route) => pathMatches(pathname, route))
	const roleRule = roleRuleForPath(pathname)

	const nextWithCsp = () => withCsp(NextResponse.next({ request: { headers: requestHeaders } }), csp)
	const redirectWithCsp = (url: URL) => withCsp(NextResponse.redirect(url), csp)

	if (!isAuthRoute && !roleRule) {
		return nextWithCsp()
	}

	const currentSession = await validateAccessSession(request)
	if (currentSession.status === 'valid') {
		const currentRole = currentSession.role
		if (isAuthRoute) {
			return redirectWithCsp(dashboardUrl(request, currentRole))
		}
		if (roleRule && !roleRule.roles.includes(currentRole)) {
			return redirectWithCsp(dashboardUrl(request, currentRole))
		}
		const lessonGate = await forcedSequenceLessonGateResponse(request, currentRole, csp, null)
		if (lessonGate) {
			return lessonGate
		}
		return nextWithCsp()
	}

	const refreshedSession = currentSession.status === 'invalid'
		? await refreshSession(request)
		: currentSession
	if (refreshedSession.status === 'valid' && 'response' in refreshedSession) {
		const refreshedCookieHeader = requestCookieHeaderWithUpstream(request, refreshedSession.response)
		const refreshedRequestHeaders = new Headers(requestHeaders)
		refreshedRequestHeaders.set('cookie', refreshedCookieHeader)
		if (isAuthRoute) {
			return withCsp(
				applyUpstreamAuthCookies(NextResponse.redirect(dashboardUrl(request, refreshedSession.role)), refreshedSession.response),
				csp,
			)
		}

		if (roleRule && !roleRule.roles.includes(refreshedSession.role)) {
			return withCsp(
				applyUpstreamAuthCookies(NextResponse.redirect(dashboardUrl(request, refreshedSession.role)), refreshedSession.response),
				csp,
			)
		}
		const refreshedLessonGate = await forcedSequenceLessonGateResponse(
			request,
			refreshedSession.role,
			csp,
			refreshedSession.response,
			refreshedCookieHeader,
		)
		if (refreshedLessonGate) {
			return refreshedLessonGate
		}
		const response = NextResponse.next({ request: { headers: refreshedRequestHeaders } })
		return withCsp(applyUpstreamAuthCookies(response, refreshedSession.response), csp)
	}

	if (currentSession.status === 'unavailable' || refreshedSession.status === 'unavailable') {
		if (isAuthRoute) {
			return nextWithCsp()
		}
		return withCsp(
			NextResponse.json(
				{ message: 'Сервис авторизации временно недоступен. Повторите попытку позже.' },
				{ status: 503, headers: { 'Retry-After': '5' } },
			),
			csp,
		)
	}

	if (isAuthRoute) {
		if (request.cookies.get(ACCESS_COOKIE) || request.cookies.get(REFRESH_COOKIE)) {
			return withCsp(clearAuthCookies(NextResponse.next({ request: { headers: requestHeaders } })), csp)
		}
		return nextWithCsp()
	}

	return withCsp(
		clearAuthCookies(NextResponse.redirect(loginUrl(request))),
		csp,
	)
}

export const config = {
	matcher: [
		{
			// All app routes: CSP + nonce; auth paths also run access checks above.
			source: '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
		},
	],
}
