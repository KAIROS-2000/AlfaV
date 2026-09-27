import { isIP } from 'node:net'

export const TRUSTED_CLIENT_IP_HEADER = 'x-progyx-client-ip'

type HeaderReader = Pick<Headers, 'get'>

/**
 * Read the single client address that the private Caddy-to-Next hop creates.
 * Browser-supplied forwarding chains are never copied to the backend.
 */
export function trustedClientIp(headers: HeaderReader): string | null {
  const value = headers.get(TRUSTED_CLIENT_IP_HEADER)?.trim() ?? ''
  if (!value || value.length > 64 || isIP(value) === 0) return null
  return value
}
