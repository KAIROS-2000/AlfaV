'use client'

import { useEffect, useState } from 'react'
import { ApiError, api } from '@/lib/api'
import { getStoredTheme } from '@/lib/theme'
import {
  getSessionSnapshot,
  setAuthenticatedSession,
  subscribeSessionSnapshot,
  type SessionSnapshot,
} from '@/lib/session-store'
import type { AuthMode } from '@/lib/api'
import type { UserItem } from '@/types'

let sessionRequest: Promise<UserItem> | null = null

function canReuseSnapshot(snapshot: SessionSnapshot, auth: AuthMode) {
  if (snapshot.status === 'authenticated') {
    return true
  }

  return auth === 'optional' && snapshot.status === 'anonymous'
}

export async function fetchSessionUser({
  auth = 'optional',
  force = false,
}: {
  auth?: AuthMode
  force?: boolean
} = {}) {
  const snapshot = getSessionSnapshot()
  if (!force && canReuseSnapshot(snapshot, auth)) {
    return snapshot.user
  }

  if (!sessionRequest) {
    // Keep the shared in-flight request independent from the first caller's
    // optional/required policy. Each caller handles an authoritative 401 below.
    sessionRequest = api<{ user: UserItem }>('/auth/me', undefined, { auth: 'required' })
      .then((result) => {
        const u = result.user
        const stored = getStoredTheme()
        const theme = stored ?? u.theme
        setAuthenticatedSession({ ...u, theme })
        return { ...u, theme }
      })
      .finally(() => {
        sessionRequest = null
      })
  }

  try {
    return await sessionRequest
  } catch (error) {
    if (error instanceof ApiError && error.status === 401 && auth === 'optional') {
      return null
    }
    throw error
  }
}

export function useSessionUser({
  auth = 'optional',
  enabled = true,
}: {
  auth?: AuthMode
  enabled?: boolean
} = {}) {
  const [snapshot, setSnapshot] = useState<SessionSnapshot>({
    status: 'unknown',
    user: null,
  })
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    setSnapshot(getSessionSnapshot())
    return subscribeSessionSnapshot((nextSnapshot) => {
      setError(null)
      setSnapshot(nextSnapshot)
    })
  }, [])

  useEffect(() => {
    if (!enabled || snapshot.status !== 'unknown') {
      return
    }

    let cancelled = false

    fetchSessionUser({ auth })
      .then(() => {
        if (!cancelled) {
          setError(null)
          setSnapshot(getSessionSnapshot())
        }
      })
      .catch((sessionError: unknown) => {
        if (!cancelled) {
          setError(sessionError instanceof Error ? sessionError : new Error('Session request failed'))
          setSnapshot(getSessionSnapshot())
        }
      })

    return () => {
      cancelled = true
    }
  }, [auth, enabled, snapshot.status])

  return {
    user: snapshot.user,
    status: snapshot.status,
    isAuthenticated: snapshot.status === 'authenticated',
    isResolved: snapshot.status !== 'unknown' || error !== null,
    error,
    refresh: () => {
      setError(null)
      return fetchSessionUser({ auth, force: true }).then((user) => {
        setSnapshot(getSessionSnapshot())
        return user
      }).catch((sessionError: unknown) => {
        setError(sessionError instanceof Error ? sessionError : new Error('Session request failed'))
        throw sessionError
      })
    },
  }
}
