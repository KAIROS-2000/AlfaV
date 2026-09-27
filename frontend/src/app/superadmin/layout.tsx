import type { Metadata } from 'next'

import { AdminAreaShell } from '@/components/admin-area-shell'
import { NO_INDEX_ROBOTS } from '@/lib/seo'

export const metadata: Metadata = {
  robots: NO_INDEX_ROBOTS,
}

export default function SuperadminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <AdminAreaShell area="superadmin">{children}</AdminAreaShell>
}
