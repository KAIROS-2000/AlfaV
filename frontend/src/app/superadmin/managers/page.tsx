import { AdminAreaShell } from '@/components/admin-area-shell'
import { SuperadminManagersPanel } from '@/components/superadmin-managers-panel'
import { serverApi } from '@/lib/server-api'
import type { AdminManagerDirectoryResponse } from '@/types'

export default async function SuperadminManagersPage() {
  const initial = await serverApi<AdminManagerDirectoryResponse>('/admin/managers?page=1&page_size=15')
  return <AdminAreaShell area='superadmin' section='managers'><SuperadminManagersPanel initialData={initial} /></AdminAreaShell>
}
