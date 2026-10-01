import { describe, expect, it } from 'vitest'
import { dashboardPathForUser } from './RoleDashboards'

describe('role dashboard destinations', () => {
  it.each([
    ['customer', '/workspace/customer'],
    ['store_owner', '/seller'],
    ['store_admin', '/seller'],
    ['support', '/seller/support'],
    ['god', '/seller/platform'],
  ])('routes active %s accounts to %s', (role, path) => {
    expect(dashboardPathForUser({ role, approval_status: 'active' })).toBe(path)
  })

  it('does not open a role dashboard before account approval', () => {
    expect(dashboardPathForUser({ role: 'store_owner', approval_status: 'pending' })).toBe('/workspace/pending')
    expect(dashboardPathForUser({ role: 'support', approval_status: 'rejected' })).toBe('/workspace/rejected')
  })

  it('routes an approved store member to the shared dashboard regardless of platform role', () => {
    expect(dashboardPathForUser({
      role: 'customer',
      approval_status: 'active',
      store_memberships: [{ store_id: 12, role: 'store_viewer', status: 'approved' }],
    })).toBe('/seller')
  })
})