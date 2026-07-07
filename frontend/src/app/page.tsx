import type { Metadata } from 'next'
import { headers } from 'next/headers'

import { HomePageContent } from '@/components/home-page'
import {
  absoluteUrl,
  createPublicMetadata,
  jsonLdScriptContent,
  SITE_DESCRIPTION,
  SITE_NAME,
} from '@/lib/seo'

export const metadata: Metadata = createPublicMetadata({
  path: '/',
  keywords: [
    'программирование для детей 7-15 лет',
    'детская IT школа',
    'обучающая платформа для школьников',
  ],
})

function homeStructuredData() {
  const organizationId = `${absoluteUrl('/')}#organization`

  return [
    {
      '@context': 'https://schema.org',
      '@type': 'EducationalOrganization',
      '@id': organizationId,
      name: SITE_NAME,
      url: absoluteUrl('/'),
      logo: absoluteUrl('/progyx-logo.png'),
      description: SITE_DESCRIPTION,
      inLanguage: 'ru-RU',
      areaServed: 'RU',
      knowsAbout: [
        'programming for kids',
        'coding lessons',
        'computer science education',
        'parent progress tracking',
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: SITE_NAME,
      url: absoluteUrl('/'),
      inLanguage: 'ru-RU',
      publisher: {
        '@id': organizationId,
      },
    },
    {
      '@context': 'https://schema.org',
      '@type': 'Course',
      name: 'Обучение программированию для школьников',
      description:
        'Маршрут обучения с уроками, практикой, кодом, прогрессом ученика и семейным доступом для родителей.',
      provider: {
        '@id': organizationId,
      },
      audience: {
        '@type': 'EducationalAudience',
        educationalRole: 'student',
      },
      inLanguage: 'ru-RU',
    },
    {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: [
        {
          '@type': 'Question',
          name: 'Для кого подходит Progyx?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Progyx подходит школьникам, которым нужен понятный маршрут изучения программирования, и родителям, которые хотят видеть прогресс без технической перегрузки.',
          },
        },
        {
          '@type': 'Question',
          name: 'Что видит ученик внутри платформы?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Ученик видит маршрут, урок, практику по программированию, задания и следующий шаг обучения.',
          },
        },
        {
          '@type': 'Question',
          name: 'Что получает родитель?',
          acceptedAnswer: {
            '@type': 'Answer',
            text: 'Родительский доступ показывает движение ребёнка по шагам, прогресс, практику и подсказки, где можно мягко помочь.',
          },
        },
      ],
    },
  ]
}

export default async function HomePage() {
  const nonce = (await headers()).get('x-nonce') ?? undefined

  return (
    <>
      <script
        type='application/ld+json'
        nonce={nonce}
        dangerouslySetInnerHTML={{
          __html: jsonLdScriptContent(homeStructuredData()),
        }}
      />
      <HomePageContent />
    </>
  )
}
