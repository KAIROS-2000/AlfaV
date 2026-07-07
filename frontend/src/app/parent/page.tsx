import type { Metadata } from 'next'
import { headers } from 'next/headers'

import { ParentLandingPageContent } from '@/components/parent-landing-page'
import { absoluteUrl, createPublicMetadata, jsonLdScriptContent } from '@/lib/seo'

export const metadata: Metadata = createPublicMetadata({
  title: 'Родительский кабинет',
  description:
    'Родительский кабинет Progyx помогает подключиться к учёбе ребёнка, видеть прогресс, практику, достижения и мягкие подсказки без технического жаргона.',
  path: '/parent',
  keywords: [
    'родительский кабинет обучения',
    'прогресс ребёнка в программировании',
    'контроль обучения детей онлайн',
  ],
})

function parentStructuredData() {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: 'Как родителю подключиться к Progyx?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Родитель создаёт аккаунт, выбирает роль родителя, получает от ребёнка короткий код из кабинета и вводит его в семейном кабинете.',
        },
      },
      {
        '@type': 'Question',
        name: 'Что видно в семейном кабинете?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'В семейном кабинете отображаются прогресс ребёнка, практика, достижения и подсказки по тем местам, где можно мягко помочь.',
        },
      },
      {
        '@type': 'Question',
        name: 'Нужно ли родителю разбираться в программировании?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Нет. Progyx показывает прогресс и следующие шаги понятным языком, без технического жаргона.',
        },
      },
    ],
    url: absoluteUrl('/parent'),
  }
}

export default async function ParentLandingPage() {
  const nonce = (await headers()).get('x-nonce') ?? undefined

  return (
    <>
      <script
        type='application/ld+json'
        nonce={nonce}
        dangerouslySetInnerHTML={{
          __html: jsonLdScriptContent(parentStructuredData()),
        }}
      />
      <ParentLandingPageContent />
    </>
  )
}
