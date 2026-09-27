export const DEFAULT_BROWSER_REQUEST_TIMEOUT_MS = 20_000
export const UPLOAD_BROWSER_REQUEST_TIMEOUT_MS = 90_000
export const DEFAULT_SERVER_REQUEST_TIMEOUT_MS = 15_000
export const AUTH_SERVER_REQUEST_TIMEOUT_MS = 8_000

export class RequestTimeoutError extends Error {
  readonly timeoutMs: number

  constructor(timeoutMs: number, cause?: unknown) {
    super(`Request timed out after ${timeoutMs} ms`)
    this.name = 'RequestTimeoutError'
    this.timeoutMs = timeoutMs
    if (cause !== undefined) {
      ;(this as Error & { cause?: unknown }).cause = cause
    }
  }
}

export function isRequestTimeoutError(error: unknown): error is RequestTimeoutError {
  return error instanceof RequestTimeoutError
}

/**
 * Applies one deadline to the complete operation (fetch plus response parsing).
 * An existing caller signal is preserved and forwarded to the internal signal.
 */
export async function withRequestTimeout<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  callerSignal?: AbortSignal | null,
): Promise<T> {
  const controller = new AbortController()
  let timedOut = false

  const forwardAbort = () => controller.abort(callerSignal?.reason)
  if (callerSignal?.aborted) {
    forwardAbort()
  } else {
    callerSignal?.addEventListener('abort', forwardAbort, { once: true })
  }

  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort(new RequestTimeoutError(timeoutMs))
  }, timeoutMs)

  try {
    return await operation(controller.signal)
  } catch (error) {
    if (timedOut) {
      throw new RequestTimeoutError(timeoutMs, error)
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
    callerSignal?.removeEventListener('abort', forwardAbort)
  }
}
