import { LegalDocumentPage } from '@/components/legal-document-page'
import { createPublicMetadata } from '@/lib/seo'

export const metadata = createPublicMetadata({
  title: 'Пользовательское соглашение',
  path: '/terms',
})

export default function TermsPage() {
  return <LegalDocumentPage kind="terms" />
}
