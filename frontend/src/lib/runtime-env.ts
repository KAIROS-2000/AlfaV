export type AppEnvironment = 'development' | 'test' | 'production'

export function normalizeEnvironmentValue(value: string | undefined | null) {
  const normalized = value?.trim().toLowerCase()
  return normalized || null
}

function asAppEnvironment(value: string | null): AppEnvironment {
  if (value === 'production' || value === 'test') return value
  return 'development'
}

/** APP_ENV is the authoritative runtime deployment mode for the portable image. */
export function getRuntimeAppEnvironment(): AppEnvironment {
  return asAppEnvironment(
    normalizeEnvironmentValue(process.env.APP_ENV)
      || normalizeEnvironmentValue(process.env.NEXT_PUBLIC_APP_ENV),
  )
}

/** Build/client mode may fall back to NODE_ENV, unlike runtime-only server settings. */
export function getBuildAppEnvironment(): AppEnvironment {
  const explicit = normalizeEnvironmentValue(process.env.APP_ENV)
    || normalizeEnvironmentValue(process.env.NEXT_PUBLIC_APP_ENV)
  return asAppEnvironment(explicit || normalizeEnvironmentValue(process.env.NODE_ENV))
}

export function isProductionRuntime() {
  return getRuntimeAppEnvironment() === 'production'
}

export function normalizeUrlSetting(
  value: string | undefined | null,
  { requireHttps = false }: { requireHttps?: boolean } = {},
) {
  const trimmed = value?.trim()
  if (!trimmed) return null

  try {
    const url = new URL(trimmed)
    if (!['http:', 'https:'].includes(url.protocol)) return null
    if (requireHttps && url.protocol !== 'https:') return null
    if (url.username || url.password || url.search || url.hash) return null
    url.pathname = url.pathname.replace(/\/+$/, '')
    return url.toString().replace(/\/$/, '')
  } catch {
    return null
  }
}

export function requireRuntimeUrl(
  name: string,
  { requireHttps = false }: { requireHttps?: boolean } = {},
) {
  const value = normalizeUrlSetting(process.env[name], { requireHttps })
  if (!value) {
    const protocolHint = requireHttps ? ' valid HTTPS' : ' valid HTTP(S)'
    throw new Error(`${name} must be set to a${protocolHint} URL when APP_ENV=production`)
  }
  return value
}
