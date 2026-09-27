import { getBuildAppEnvironment } from './runtime-env'

function getAppEnv() {
  return getBuildAppEnvironment()
}

function getPublicApiPath() {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim() || '/api'
  if (!configured.startsWith('/') || configured.startsWith('//')) {
    throw new Error(
      'NEXT_PUBLIC_API_URL must be a same-origin path (normally /api); configure INTERNAL_API_URL for the upstream API',
    )
  }
  return configured.replace(/\/$/, '') || '/api'
}

export const PUBLIC_APP_ENV = getAppEnv()
export const PUBLIC_IS_PRODUCTION = PUBLIC_APP_ENV === 'production'
export const PUBLIC_API_URL = getPublicApiPath()
