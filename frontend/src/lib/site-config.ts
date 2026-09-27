export type PublicSiteConfig = {
  configured: boolean
  supportEmail: string | null
  supportPhone: string | null
  supportPhoneHref: string | null
  legalName: string | null
  taxId: string | null
  registrationNumber: string | null
  legalAddress: string | null
  legalDocumentVersion: string
  legalEffectiveDate: string | null
}

export type RegistrationLegalConfig = Pick<
  PublicSiteConfig,
  'legalDocumentVersion' | 'legalEffectiveDate'
>

export type LegalDocumentKind = 'privacy' | 'terms' | 'personal-data'

export const DEVELOPMENT_LEGAL_DOCUMENT_VERSION = 'development-v1'

export function resolveLegalDocumentVersion(
  configuredVersion: string | null,
  isProduction: boolean,
) {
  return configuredVersion || (isProduction ? 'unconfigured' : DEVELOPMENT_LEGAL_DOCUMENT_VERSION)
}
