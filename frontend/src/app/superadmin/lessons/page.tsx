import { AdminAreaShell } from '@/components/admin-area-shell'
import { AdminLessonsPanel } from '@/components/admin-tools'
import { serverApi } from '@/lib/server-api'
import type { AdminModulesResponse } from '@/types'

export default async function SuperadminLessonsPage() {
  const modules = await serverApi<AdminModulesResponse>('/admin/modules?page=1&page_size=15')

  return (
    <AdminAreaShell area="superadmin" section="lessons">
      <AdminLessonsPanel
        initialData={modules}
        moduleHubHref="/superadmin/modules"
        lessonBaseHref="/superadmin/lessons"
      />
    </AdminAreaShell>
  )
}
