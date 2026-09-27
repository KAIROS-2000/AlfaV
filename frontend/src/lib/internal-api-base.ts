import {
	isProductionRuntime,
	normalizeUrlSetting,
	requireRuntimeUrl,
} from '@/lib/runtime-env'

/** API base usable from `proxy.ts` (avoid importing `server-only` server-env). */
export function getInternalApiBaseUrl(): string {
	if (isProductionRuntime()) {
		return requireRuntimeUrl('INTERNAL_API_URL')
	}
	return normalizeUrlSetting(process.env.INTERNAL_API_URL) || 'http://localhost:8000/api'
}
