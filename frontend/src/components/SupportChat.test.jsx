import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SupportChatPanel } from './SupportChat'

vi.mock('../lib/i18n', () => ({
  useI18n: () => ({ t: (key) => key, date: () => 'Oct 2, 2026, 10:30 AM' }),
}))
vi.mock('./ui', () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
  Icon: () => <span aria-hidden="true" />,
}))

afterEach(() => cleanup())

describe('support chat panel', () => {
  it('shows each message with its own localized timestamp', () => {
    render(<SupportChatPanel
      title="Customer"
      conversation={{ messages: [{ id: 1, role: 'user', content: 'Where is my order?', created_at: '2026-10-02T10:30:00Z' }] }}
      onReply={vi.fn()}
    />)

    expect(screen.getByText('Where is my order?')).toBeTruthy()
    expect(screen.getByText('Oct 2, 2026, 10:30 AM')).toBeTruthy()
    expect(screen.getByRole('article').className).toContain('user')
  })
})