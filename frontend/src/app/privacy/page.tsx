import { LegalDocumentPage } from '@/components/legal-document-page'
import { createPublicMetadata } from '@/lib/seo'

export const metadata = createPublicMetadata({
  title: 'Политика конфиденциальности',
  path: '/privacy',
})

export default function PrivacyPage() {
  return <LegalDocumentPage kind="privacy" />
}
