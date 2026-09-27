import { serverApi } from '@/lib/server-api'
import { TeacherLessonBuilder } from '@/components/teacher-lesson-builder'
import { TeacherClassDetail, TeacherOverviewData } from '@/types'

interface TeacherLessonCreationPageProps {
  searchParams?: Promise<{
    classId?: string
    fromLessonId?: string
  }>
}

export default async function TeacherLessonCreationPage({ searchParams }: TeacherLessonCreationPageProps) {
  const params = await searchParams
  const initialClassId = params?.classId ? Number(params.classId) : null
  const sourceLessonId = params?.fromLessonId ? Number(params.fromLessonId) : null
  const initialOverview = await serverApi<TeacherOverviewData>('/teacher/overview?page=1&page_size=15')
  const selectedClassDetail = Number.isFinite(initialClassId) && !initialOverview?.classes.some(item => item.id === initialClassId)
    ? await serverApi<TeacherClassDetail>(`/teacher/classes/${initialClassId}?students_page=1&assignments_page=1&page_size=15`)
    : null
  const initialClasses = selectedClassDetail
    ? [selectedClassDetail.classroom, ...(initialOverview?.classes ?? [])]
    : initialOverview?.classes ?? []

  return (
    <main>
      <TeacherLessonBuilder
        initialClasses={initialClasses}
        initialPagination={initialOverview?.classes_pagination ?? null}
        initialClassId={Number.isFinite(initialClassId) ? initialClassId : null}
        sourceLessonId={Number.isFinite(sourceLessonId) ? sourceLessonId : null}
      />
    </main>
  )
}
