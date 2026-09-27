import 'server-only'

import { isProductionRuntime } from '@/lib/runtime-env'
import {
  resolveLegalDocumentVersion,
  type LegalDocumentKind,
  type PublicSiteConfig,
} from '@/lib/site-config'

const DOCUMENT_ENV: Record<LegalDocumentKind, string> = {
  privacy: 'LEGAL_PRIVACY_CONTENT',
  terms: 'LEGAL_TERMS_CONTENT',
  'personal-data': 'LEGAL_PERSONAL_DATA_CONTENT',
}

const DOCUMENT_TITLE: Record<LegalDocumentKind, string> = {
  privacy: 'Политика конфиденциальности',
  terms: 'Пользовательское соглашение',
  'personal-data': 'Обработка персональных данных',
}

function setting(name: string) {
  return process.env[name]?.trim() || null
}

function requiredProductionSetting(name: string) {
  const value = setting(name)
  if (!value && isProductionRuntime()) {
    throw new Error(`${name} must be set when APP_ENV=production`)
  }
  return value
}

function phoneHref(value: string | null) {
  if (!value) return null
  const normalized = value.replace(/[^+\d]/g, '')
  return normalized ? `tel:${normalized}` : null
}

export function getPublicSiteConfig(): PublicSiteConfig {
  const supportEmail = requiredProductionSetting('LEGAL_SUPPORT_EMAIL')
  const supportPhone = requiredProductionSetting('LEGAL_SUPPORT_PHONE')
  const legalName = requiredProductionSetting('LEGAL_OPERATOR_NAME')
  const taxId = requiredProductionSetting('LEGAL_OPERATOR_TAX_ID')
  const registrationNumber = requiredProductionSetting('LEGAL_OPERATOR_REGISTRATION_ID')
  const legalAddress = requiredProductionSetting('LEGAL_OPERATOR_ADDRESS')
  const legalDocumentVersion = requiredProductionSetting('LEGAL_DOCUMENTS_VERSION')
  const legalEffectiveDate = setting('LEGAL_DOCUMENTS_EFFECTIVE_DATE')

  // Validate all operator-approved documents at application start/render time.
  Object.values(DOCUMENT_ENV).forEach(requiredProductionSetting)

  const configured = Boolean(
    supportEmail &&
      supportPhone &&
      legalName &&
      taxId &&
      registrationNumber &&
      legalAddress &&
      legalDocumentVersion
  )

  return {
    configured,
    supportEmail,
    supportPhone,
    supportPhoneHref: phoneHref(supportPhone),
    legalName,
    taxId,
    registrationNumber,
    legalAddress,
    legalDocumentVersion: resolveLegalDocumentVersion(legalDocumentVersion, isProductionRuntime()),
    legalEffectiveDate,
  }
}

export function getLegalDocument(kind: LegalDocumentKind) {
  const config = getPublicSiteConfig()
  const content = requiredProductionSetting(DOCUMENT_ENV[kind])
  return {
    ...config,
    title: DOCUMENT_TITLE[kind],
    content,
  }
}
