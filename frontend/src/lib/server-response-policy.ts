export type ServerRouteRedirect = '/auth/login' | '/dashboard' | null

export function redirectForServerStatus(status: number): ServerRouteRedirect {
  if (status === 401) return '/auth/login'
  if (status === 403) return '/dashboard'
  return null
}

export class ServerApiResponseError extends Error {
  readonly status: number
  readonly payload: unknown

  constructor(status: number, message: string, payload: unknown) {
    super(message)
    this.name = 'ServerApiResponseError'
    this.status = status
    this.payload = payload
  }
}
