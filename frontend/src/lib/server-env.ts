import 'server-only'

import { getInternalApiBaseUrl } from '@/lib/internal-api-base'

export function getInternalApiUrl() {
  return getInternalApiBaseUrl()
}
