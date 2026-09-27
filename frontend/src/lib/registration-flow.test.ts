import assert from 'node:assert/strict'
import test from 'node:test'

import { awaitsParentPasswordSetup } from './registration-flow.ts'

test('parent password-setup registration must remain anonymous', () => {
  assert.equal(
    awaitsParentPasswordSetup({
      user: { role: 'parent' },
      requires_password_setup: true,
      requires_login_after_password_setup: true,
    }),
    true,
  )
})

test('active dev parent and student registration do not enter setup state', () => {
  assert.equal(
    awaitsParentPasswordSetup({ user: { role: 'parent' }, requires_password_setup: false }),
    false,
  )
  assert.equal(
    awaitsParentPasswordSetup({ user: { role: 'student' }, requires_password_setup: true }),
    false,
  )
})
