import 'server-only'

import type { Metadata } from 'next'

export const SITE_NAME = 'Progyx'
export const SITE_TITLE = 'Progyx - обучение программированию для школьников'
export const SITE_DESCRIPTION =
  'Progyx - образовательная платформа по программированию для школьников: маршрут обучения, уроки, практика, прогресс и родительский кабинет.'

export const SITE_KEYWORDS = [
  'Progyx',
  'обучение программированию для школьников',
  'курсы программирования для детей',
  'онлайн уроки программирования',
  'IT обучение для детей',
  'родительский кабинет обучения',
  'практика программирования',
]

export const PUBLIC_ROUTES = [
  {
    path: '/',
    priority: 1,
    changeFrequency: 'weekly',
  },
  {
    path: '/parent',
    priority: 0.85,
    changeFrequency: 'monthly',
  },
  {
    path: '/it-career',
    priority: 0.8,
    changeFrequency: 'monthly',
  },
  {
    path: '/tournament',
    priority: 0.65,
    changeFrequency: 'daily',
  },
] as const

export const PRIVATE_ROBOTS_PATHS = [
  '/api/',
  '/auth/',
  '/dashboard',
  '/messages',
  '/roadmap',
  '/lessons',
  '/leaderboard',
  '/profile',
  '/useful',
  '/teacher',
  '/admin',
  '/superadmin',
  '/parent/dashboard',
  '/support',
  '/bug-hunter',
  '/forgot-password',
  '/reset-password',
  '/verify-email',
]

export const NO_INDEX_ROBOTS: Metadata['robots'] = {
  index: false,
  follow: false,
  googleBot: {
    index: false,
    follow: false,
    noimageindex: true,
  },
}

function normalizeSiteUrl(value: string | undefined | null) {
  const trimmed = value?.trim()
  if (!trimmed) return null

  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`

  try {
    const url = new URL(withProtocol)
    url.pathname = url.pathname.replace(/\/+$/, '')
    url.search = ''
    url.hash = ''
    return url.toString().replace(/\/$/, '')
  } catch {
    return null
  }
}

export function getSiteUrl() {
  return (
    normalizeSiteUrl(process.env.NEXT_PUBLIC_SITE_URL) ||
    normalizeSiteUrl(process.env.FRONTEND_PUBLIC_URL) ||
    normalizeSiteUrl(process.env.CLIENT_URL) ||
    normalizeSiteUrl(process.env.VERCEL_PROJECT_PRODUCTION_URL) ||
    normalizeSiteUrl(process.env.VERCEL_URL) ||
    'http://localhost:3000'
  )
}

export function absoluteUrl(path = '/') {
  return new URL(path, `${getSiteUrl()}/`).toString()
}

export function createPublicMetadata({
  title,
  description = SITE_DESCRIPTION,
  path = '/',
  keywords = [],
}: {
  title?: string
  description?: string
  path?: string
  keywords?: string[]
} = {}): Metadata {
  const brandedTitle = title ? `${title} | ${SITE_NAME}` : SITE_TITLE

  const metadata: Metadata = {
    description,
    keywords: [...SITE_KEYWORDS, ...keywords],
    alternates: {
      canonical: path,
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-image-preview': 'large',
        'max-snippet': -1,
        'max-video-preview': -1,
      },
    },
    openGraph: {
      title: brandedTitle,
      description,
      url: path,
      siteName: SITE_NAME,
      locale: 'ru_RU',
      type: 'website',
      images: [
        {
          url: '/progyx-logo.png',
          width: 512,
          height: 512,
          alt: 'Логотип Progyx',
        },
      ],
    },
    twitter: {
      card: 'summary',
      title: brandedTitle,
      description,
      images: ['/progyx-logo.png'],
    },
  }

  if (title) {
    metadata.title = title
  }

  return metadata
}

export function jsonLdScriptContent(data: unknown) {
  return JSON.stringify(data).replace(/</g, '\\u003c')
}
