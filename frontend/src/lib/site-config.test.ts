import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveLegalDocumentVersion } from './site-config.ts'

test('development registration uses the backend legal-document fallback', () => {
  assert.equal(resolveLegalDocumentVersion(null, false), 'development-v1')
})

test('production registration keeps an explicit configuration requirement', () => {
  assert.equal(resolveLegalDocumentVersion(null, true), 'unconfigured')
  assert.equal(resolveLegalDocumentVersion('approved-v2', true), 'approved-v2')
})
