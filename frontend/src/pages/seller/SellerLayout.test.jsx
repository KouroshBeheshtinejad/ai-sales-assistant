import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import SellerLayout from './SellerLayout'

const mocks = vi.hoisted(() => ({ user: null, store: null, signOut: vi.fn() }))

vi.mock('../../components/Layout', () => ({
  Brand: () => <span>NAVA</span>,
  LocaleToggle: () => <button type="button">Language</button>,
  SkipLink: () => null,
}))
vi.mock('../../components/ui', () => ({
  Button: ({ children }) => <button type="button">{children}</button>,
  Empty: ({ title }) => <p>{title}</p>,
  ErrorNote: () => null,
  Field: ({ children }) => <div>{children}</div>,
  Icon: () => <span aria-hidden="true" />,
  Loading: () => <p>Loading</p>,
  Modal: () => null,
}))
vi.mock('../../lib/auth', () => ({ useAuth: () => ({ user: mocks.user, signOut: mocks.signOut }) }))
vi.mock('../../lib/i18n', () => ({ useI18n: () => ({ t: (key) => key }) }))
vi.mock('../../lib/api', () => ({ api: { support: { summary: () => Promise.resolve({ attention_count: 0 }) } } }))
vi.mock('../../lib/hooks', () => ({ useAsync: () => ({ data: { attention_count: 0 } }) }))
vi.mock('./SellerContext', () => ({
  SellerProvider: ({ children }) => children,
  useSeller: () => ({ stores: mocks.store ? [mocks.store] : [], store: mocks.store, select: vi.fn(), loading: false, error: null, reloadStores: vi.fn() }),
}))

describe('role-aware seller navigation', () => {
  afterEach(() => cleanup())

  it('shows store and customer tabs together for an approved customer member', () => {
    mocks.user = { role: 'customer' }
    mocks.store = { id: 3, name: 'Store', permissions: ['store.read', 'order.read', 'member.read'] }
    render(<MemoryRouter><SellerLayout /></MemoryRouter>)

    expect(screen.getAllByText('s.orders').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dash.team').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dash.customer').length).toBeGreaterThan(0)
  })

  it('does not show store management tabs without store permissions', () => {
    mocks.user = { role: 'customer' }
    mocks.store = null
    render(<MemoryRouter><SellerLayout /></MemoryRouter>)

    expect(screen.queryByText('dash.team')).toBeNull()
    expect(screen.queryByText('s.products')).toBeNull()
  })
})
