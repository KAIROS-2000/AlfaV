import type { MetadataRoute } from 'next'

import { SITE_DESCRIPTION, SITE_NAME } from '@/lib/seo'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: SITE_NAME,
    short_name: SITE_NAME,
    description: SITE_DESCRIPTION,
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#f8fafc',
    theme_color: '#0f172a',
    lang: 'ru',
    icons: [
      {
        src: '/tab-icon.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/progyx-logo.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  }
}
