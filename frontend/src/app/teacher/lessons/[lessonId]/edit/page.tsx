import { TeacherLessonEditor } from '@/components/lesson-authoring-editors'
import { notFound } from 'next/navigation'

export default async function TeacherLessonEditPage({
  params,
}: {
  params: Promise<{ lessonId: string }>
}) {
  const { lessonId } = await params
  if (!/^\d+$/.test(lessonId)) notFound()
  return <TeacherLessonEditor lessonId={Number(lessonId)} />
}
