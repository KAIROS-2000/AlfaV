import assert from 'node:assert/strict'
import test from 'node:test'

import { rejectedResults } from './settled-results.ts'

test('rejectedResults preserves only failures and their reasons', async () => {
  const results = await Promise.allSettled([
    Promise.resolve('ready'),
    Promise.reject(new Error('digest unavailable')),
    Promise.resolve(3),
  ])
  const failed = rejectedResults(results)

  assert.equal(failed.length, 1)
  assert.equal((failed[0].reason as Error).message, 'digest unavailable')
})
