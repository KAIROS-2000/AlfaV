import type { Metadata, Viewport } from 'next'
import { headers } from 'next/headers'
import { AppToaster } from '@/components/app-toaster'
import { MascotOverlay } from '@/components/mascot-overlay'
import { SiteChrome } from '@/components/site-chrome'
import { SiteFooter } from '@/components/site-footer'
import { ThemeHydrator } from '@/components/theme-hydrator'
import {
  getSiteUrl,
  SITE_DESCRIPTION,
  SITE_KEYWORDS,
  SITE_NAME,
  SITE_TITLE,
} from '@/lib/seo'
import { getThemeInitScript } from '@/lib/theme'
import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL(getSiteUrl()),
  applicationName: SITE_NAME,
  title: {
    default: SITE_TITLE,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  keywords: SITE_KEYWORDS,
  authors: [{ name: SITE_NAME }],
  creator: SITE_NAME,
  publisher: SITE_NAME,
  category: 'education',
  manifest: '/manifest.webmanifest',
  alternates: {
    canonical: '/',
  },
  referrer: 'strict-origin-when-cross-origin',
  icons: {
    icon: '/tab-icon.png',
    shortcut: '/tab-icon.png',
    apple: '/tab-icon.png',
  },
  openGraph: {
    type: 'website',
    locale: 'ru_RU',
    siteName: SITE_NAME,
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    url: '/',
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
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    images: ['/progyx-logo.png'],
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const headersList = await headers()
  const nonce = headersList.get('x-nonce') ?? ''

  return (
    <html lang="ru" data-theme="light" suppressHydrationWarning>
      <head>
        <script
          nonce={nonce}
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: getThemeInitScript() }}
        />
      </head>
      <body>
        <ThemeHydrator />
        <AppToaster />
        <MascotOverlay />
        <SiteChrome />
        {children}
        <SiteFooter />
      </body>
    </html>
  )
}
