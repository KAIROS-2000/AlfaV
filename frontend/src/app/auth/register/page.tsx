import { RegisterPageClient } from '@/components/register-page-client'
import { getPublicSiteConfig } from '@/lib/server-site-config'

export default function RegisterPage() {
  const config = getPublicSiteConfig()
  return (
    <RegisterPageClient
      legalConfig={{
        legalDocumentVersion: config.legalDocumentVersion,
        legalEffectiveDate: config.legalEffectiveDate,
      }}
    />
  )
}
