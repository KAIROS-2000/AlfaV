/**
 * Corporate-domain gate for staff (teacher/admin) accounts — UX layer only.
 *
 * The backend (backend/app/core/security.py `is_corporate_staff_email`) is the
 * source of truth and rejects non-corporate staff even if these checks are
 * bypassed. `GET /api/auth/options` returns the live `staff_email_domain`;
 * `DEFAULT_STAFF_EMAIL_DOMAIN` is the fallback used when options are not loaded
 * (e.g. the superadmin admin-tools screen, which does not fetch options).
 */
export const DEFAULT_STAFF_EMAIL_DOMAIN = 'progyx.pro'

/** True when `email` ends exactly with `@<domain>` (subdomains are rejected). */
export function isCorporateStaffEmail(
	email: string,
	domain: string = DEFAULT_STAFF_EMAIL_DOMAIN,
): boolean {
	const normalizedDomain = domain.trim().replace(/^@+/, '').toLowerCase()
	if (!normalizedDomain) return true
	return email.trim().toLowerCase().endsWith('@' + normalizedDomain)
}
