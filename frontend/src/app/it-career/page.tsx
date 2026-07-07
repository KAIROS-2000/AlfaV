import type { Metadata } from 'next'

import { ItCareerPage } from '@/components/it-career-page'
import { createPublicMetadata } from '@/lib/seo'

export const metadata: Metadata = createPublicMetadata({
	title: 'Перспективы работы в IT',
	description:
		'Вакансии, зарплаты, направления и перспективы IT-профессий для школьников, учеников и родителей Progyx.',
	path: '/it-career',
	keywords: [
		'перспективы работы в IT',
		'IT профессии для школьников',
		'как ребёнку выбрать IT направление',
	],
})

export default function Page() {
	return <ItCareerPage />
}
