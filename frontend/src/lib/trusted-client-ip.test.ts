import assert from 'node:assert/strict'
import test from 'node:test'

import { TRUSTED_CLIENT_IP_HEADER, trustedClientIp } from './trusted-client-ip.ts'

function headersWith(value?: string) {
  const headers = new Headers()
  if (value !== undefined) headers.set(TRUSTED_CLIENT_IP_HEADER, value)
  return headers
}

test('trusted ingress IPv4 and IPv6 addresses remain distinct', () => {
  assert.equal(trustedClientIp(headersWith('203.0.113.10')), '203.0.113.10')
  assert.equal(trustedClientIp(headersWith('203.0.113.11')), '203.0.113.11')
  assert.equal(trustedClientIp(headersWith('2001:db8::10')), '2001:db8::10')
})

test('forwarding chains and malformed client addresses are rejected', () => {
  assert.equal(trustedClientIp(headersWith('203.0.113.10, 10.0.0.1')), null)
  assert.equal(trustedClientIp(headersWith('203.0.113.10:443')), null)
  assert.equal(trustedClientIp(headersWith('unknown')), null)
  assert.equal(trustedClientIp(headersWith()), null)
})
