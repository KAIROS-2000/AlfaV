import { ContactsPanel } from '@/components/staff-outreach-panels'
import { serverApi } from '@/lib/server-api'
import type { ContactsDirectoryResponse } from '@/types'

export default async function SuperadminContactsPage() {
  const initial = await serverApi<ContactsDirectoryResponse>('/admin/contacts?page=1&page_size=20').catch(() => null)
  return <ContactsPanel area='superadmin' initial={initial} />
}
