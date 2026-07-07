import type { MetadataRoute } from 'next'

import { absoluteUrl, getSiteUrl, PRIVATE_ROBOTS_PATHS } from '@/lib/seo'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: PRIVATE_ROBOTS_PATHS,
    },
    sitemap: absoluteUrl('/sitemap.xml'),
    host: getSiteUrl(),
  }
}
