import assert from 'node:assert/strict'
import test from 'node:test'

import {
  isRoleAllowedForPath,
  homePathForRole,
  pathMatchesRoute,
  roleRuleForPath,
} from './route-access.ts'

test('parent dashboard is protected and parent-only', () => {
  const rule = roleRuleForPath('/parent/dashboard')

  assert.ok(rule)
  assert.deepEqual(rule.roles, ['parent'])
  assert.equal(isRoleAllowedForPath('/parent/dashboard', 'parent'), true)
  assert.equal(isRoleAllowedForPath('/parent/dashboard', 'student'), false)
  assert.equal(isRoleAllowedForPath('/parent/dashboard/settings', 'admin'), false)
})

test('staff route prefixes enforce their role boundaries', () => {
  assert.equal(isRoleAllowedForPath('/teacher/lessons', 'teacher'), true)
  assert.equal(isRoleAllowedForPath('/teacher/lessons', 'admin'), false)
  assert.equal(isRoleAllowedForPath('/manager/contacts', 'manager'), true)
  assert.equal(isRoleAllowedForPath('/admin/users', 'superadmin'), true)
  assert.equal(isRoleAllowedForPath('/superadmin/users', 'admin'), false)
})

test('route matching does not confuse sibling prefixes', () => {
  assert.equal(pathMatchesRoute('/admin', '/admin'), true)
  assert.equal(pathMatchesRoute('/admin/users', '/admin'), true)
  assert.equal(pathMatchesRoute('/administrator', '/admin'), false)
  assert.equal(roleRuleForPath('/public'), null)
})

test('each authenticated role has a non-looping home route', () => {
  assert.equal(homePathForRole('student'), '/dashboard')
  assert.equal(homePathForRole('parent'), '/parent/dashboard')
  assert.equal(homePathForRole('teacher'), '/teacher')
  assert.equal(homePathForRole('manager'), '/manager/contacts')
  assert.equal(homePathForRole('admin'), '/admin/users')
  assert.equal(homePathForRole('superadmin'), '/superadmin/users')
})
