import { AdminBugHunterPageView } from '@/components/admin-bug-hunter-page-view'
import { serverApi } from '@/lib/server-api'
import type { UserItem } from '@/types'
import { redirect } from 'next/navigation'

export default async function SuperadminBugHunterPage() {
	const session = await serverApi<{ user: UserItem }>('/auth/me').catch(() => null)
	if (!session?.user) {
		redirect('/auth/login')
	}
	if (session.user.role !== 'superadmin') {
		redirect('/dashboard')
	}

	return <AdminBugHunterPageView area='superadmin' />
}
