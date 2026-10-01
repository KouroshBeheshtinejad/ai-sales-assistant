import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Team from './Team'

const mocks = vi.hoisted(() => ({
  addMember: vi.fn(),
  updateMember: vi.fn(),
  reload: vi.fn(),
  toast: vi.fn(),
}))

vi.mock('../../lib/api', () => ({
  api: { seller: { addMember: mocks.addMember, updateMember: mocks.updateMember } },
}))
vi.mock('../../lib/hooks', () => ({
  useAsync: () => ({
    data: [{ id: 7, user_id: 12, email: 'new-member@example.com', name: 'New Member', role: 'store_viewer', status: 'pending' }],
    loading: false,
    error: null,
    reload: mocks.reload,
  }),
  useSeo: vi.fn(),
}))
vi.mock('../../lib/i18n', () => ({
  useI18n: () => ({ t: (key) => key, err: (error) => error.message }),
}))
vi.mock('../../components/ui', async () => {
  const actual = await vi.importActual('../../components/ui')
  return { ...actual, useToast: () => mocks.toast }
})
vi.mock('./SellerContext', () => ({ useSeller: () => ({ store: { id: 3, name: 'Store', permissions: ['member.read', 'member.invite', 'member.approve'] } }) }))
vi.mock('./SellerLayout', () => ({
  NeedStore: () => null,
  PageHead: ({ title }) => <h1>{title}</h1>,
}))

describe('Team membership management', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => cleanup())

  it('shows pending members and approves them through the membership API', async () => {
    mocks.updateMember.mockResolvedValue({ status: 'approved' })
    render(<Team />)

    expect(screen.getByText('new-member@example.com')).toBeTruthy()
    expect(screen.getByText('dash.memberStatus.pending')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'dash.approve' }))

    await waitFor(() => expect(mocks.updateMember).toHaveBeenCalledWith(3, 7, { status: 'approved' }))
    expect(mocks.reload).toHaveBeenCalled()
  })

  it('adds a registered account with the selected store role', async () => {
    mocks.addMember.mockResolvedValue({ id: 8 })
    render(<Team />)
    fireEvent.change(screen.getByLabelText('dash.email'), { target: { value: 'staff@example.com' } })
    fireEvent.change(screen.getByLabelText('dash.role'), { target: { value: 'store_manager' } })
    fireEvent.click(screen.getByRole('button', { name: 'dash.addMember' }))

    await waitFor(() => expect(mocks.addMember).toHaveBeenCalledWith(3, {
      email: 'staff@example.com',
      role: 'store_manager',
    }))
  })
})
