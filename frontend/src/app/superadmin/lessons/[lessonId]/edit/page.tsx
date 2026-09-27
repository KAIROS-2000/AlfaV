import { AdminAreaShell } from '@/components/admin-area-shell'
import { AdminLessonEditor } from '@/components/lesson-authoring-editors'
import { notFound } from 'next/navigation'

export default async function SuperadminLessonEditPage({
  params,
}: {
  params: Promise<{ lessonId: string }>
}) {
  const { lessonId } = await params
  if (!/^\d+$/.test(lessonId)) notFound()
  return (
    <AdminAreaShell area='superadmin' section='lessons'>
      <AdminLessonEditor lessonId={Number(lessonId)} listHref='/superadmin/lessons' />
    </AdminAreaShell>
  )
}
