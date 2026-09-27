import type { NextConfig } from 'next'
import { getBuildAppEnvironment } from './src/lib/runtime-env'

const appEnv = getBuildAppEnvironment()

// Public browser traffic uses the stable same-origin `/api` route. Runtime
// server validation of INTERNAL_API_URL is performed in src/lib/server-env.ts,
// so this portable image is not tied to an environment-specific build arg.

const securityHeaders = [
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Permitted-Cross-Domain-Policies', value: 'none' },
]

if (appEnv === 'production') {
  securityHeaders.push({
    key: 'Strict-Transport-Security',
    value: 'max-age=31536000; includeSubDomains',
  })
}

// CSP is owned by src/proxy.ts (nonce-based, per-request; Next 16 proxy replaces middleware).
// Only static security headers that don't need nonces live here.
const nextConfig: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    root: process.cwd(),
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ]
  },
}

export default nextConfig
