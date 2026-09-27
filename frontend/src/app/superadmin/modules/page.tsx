import { AdminAreaShell } from '@/components/admin-area-shell'
import { AdminModulesPanel } from '@/components/admin-tools'
import { serverApi } from '@/lib/server-api'
import type { AdminModulesResponse } from '@/types'

export default async function SuperadminModulesPage() {
  const modules = await serverApi<AdminModulesResponse>('/admin/modules?page=1&page_size=15')

  return (
    <AdminAreaShell area="superadmin" section="modules">
      <AdminModulesPanel initialData={modules} />
    </AdminAreaShell>
  )
}
