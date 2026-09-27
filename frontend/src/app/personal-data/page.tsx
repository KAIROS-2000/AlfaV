import { LegalDocumentPage } from '@/components/legal-document-page'
import { createPublicMetadata } from '@/lib/seo'

export const metadata = createPublicMetadata({
  title: 'Обработка персональных данных',
  path: '/personal-data',
})

export default function PersonalDataPage() {
  return <LegalDocumentPage kind="personal-data" />
}
