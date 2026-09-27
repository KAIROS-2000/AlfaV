import { TeacherLessonLifecycleLists } from '@/components/lesson-lifecycle-lists'
import { serverApi } from '@/lib/server-api'
import type { TeacherOverviewData } from '@/types'

export default async function TeacherLessonsPage() {
  const overview = await serverApi<TeacherOverviewData>('/teacher/overview?page=1&page_size=15')

  return (
    <main className='teacher-page'>
      <div className='teacher-page__shell page-shell mx-auto w-full max-w-[96rem] space-y-6'>
        <TeacherLessonLifecycleLists initialClasses={overview?.classes ?? null} initialClassesPagination={overview?.classes_pagination ?? null} />
      </div>
    </main>
  )
}
