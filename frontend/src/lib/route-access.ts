export type UserRole = 'student' | 'teacher' | 'parent' | 'manager' | 'admin' | 'superadmin'

export const KNOWN_ROLES: readonly UserRole[] = [
  'student',
  'teacher',
  'parent',
  'manager',
  'admin',
  'superadmin',
]

const ROLE_HOME: Record<UserRole, string> = {
  student: '/dashboard',
  parent: '/parent/dashboard',
  teacher: '/teacher',
  manager: '/manager/contacts',
  admin: '/admin/users',
  superadmin: '/superadmin/users',
}

export function homePathForRole(role: UserRole) {
  return ROLE_HOME[role]
}

export type RouteRoleRule = Readonly<{
  path: string
  roles: readonly UserRole[]
}>

export const ROLE_RULES: readonly RouteRoleRule[] = [
  { path: '/dashboard', roles: KNOWN_ROLES },
  { path: '/messages', roles: ['student', 'teacher', 'parent', 'manager'] },
  { path: '/roadmap', roles: KNOWN_ROLES },
  { path: '/lessons', roles: KNOWN_ROLES },
  { path: '/leaderboard', roles: KNOWN_ROLES },
  { path: '/profile', roles: KNOWN_ROLES },
  { path: '/useful', roles: KNOWN_ROLES },
  { path: '/parent/dashboard', roles: ['parent'] },
  { path: '/teacher', roles: ['teacher'] },
  { path: '/manager', roles: ['manager'] },
  { path: '/admin', roles: ['admin', 'superadmin'] },
  { path: '/superadmin', roles: ['superadmin'] },
]

export function pathMatchesRoute(pathname: string, target: string) {
  return pathname === target || pathname.startsWith(`${target}/`)
}

export function roleRuleForPath(pathname: string) {
  return ROLE_RULES.find(rule => pathMatchesRoute(pathname, rule.path)) ?? null
}

export function isKnownRole(value: string | undefined | null): value is UserRole {
  return Boolean(value && KNOWN_ROLES.includes(value as UserRole))
}

export function isRoleAllowedForPath(pathname: string, role: UserRole) {
  const rule = roleRuleForPath(pathname)
  return !rule || rule.roles.includes(role)
}
