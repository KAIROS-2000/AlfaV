import assert from 'node:assert/strict'
import test from 'node:test'

import { redirectForServerStatus } from './server-response-policy.ts'

test('server route auth failures map to safe destinations', () => {
  assert.equal(redirectForServerStatus(401), '/auth/login')
  assert.equal(redirectForServerStatus(403), '/dashboard')
})

test('server and timeout failures remain errors for the route boundary', () => {
  assert.equal(redirectForServerStatus(500), null)
  assert.equal(redirectForServerStatus(502), null)
  assert.equal(redirectForServerStatus(504), null)
})
