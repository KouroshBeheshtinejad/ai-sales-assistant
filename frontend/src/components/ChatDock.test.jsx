import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ChatDock from './ChatDock'

const { chat } = vi.hoisted(() => ({ chat: vi.fn() }))
vi.mock('../lib/api', () => ({ api: { chat } }))
vi.mock('../lib/i18n', () => ({
  useI18n: () => ({ t: (key) => key, err: (error) => error.message }),
}))
vi.mock('./ui', () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
  Icon: () => <span aria-hidden="true" />,
}))

afterEach(() => cleanup())

const shop = {
  storeId: 1,
  cartCount: 0,
  getGuestToken: vi.fn(),
  remember: vi.fn(),
  refreshCart: vi.fn(),
  reloadCatalog: vi.fn(),
}

describe('store chat dock', () => {
  it('sends only once when the form is submitted repeatedly while pending', async () => {
    let resolveChat
    chat.mockImplementation(() => new Promise((resolve) => { resolveChat = resolve }))
    const { container, getByRole } = render(
      <ChatDock shop={shop} storeName="Nava Shop" onClose={vi.fn()} onDraftUsed={vi.fn()} />,
    )
    fireEvent.change(getByRole('textbox'), { target: { value: 'Need help' } })
    const form = container.querySelector('form')

    fireEvent.submit(form)
    fireEvent.submit(form)

    expect(chat).toHaveBeenCalledTimes(1)
    resolveChat({ answer: 'I can help', guest_token: 'guest' })
  })

  it('shows the store logo in the chat header when available', () => {
    const { container } = render(
      <ChatDock shop={shop} storeName="Nava Shop" storeLogoUrl="/uploads/store-logo.png" onClose={vi.fn()} onDraftUsed={vi.fn()} />,
    )

    const avatar = container.querySelector('.chat-avatar')
    expect(avatar.tagName).toBe('IMG')
    expect(avatar.getAttribute('src')).toBe('/uploads/store-logo.png')
  })
})