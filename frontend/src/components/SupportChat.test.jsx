import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  it('sends only once when the reply form is submitted repeatedly while pending', async () => {
    let resolveReply
    const onReply = vi.fn(() => new Promise((resolve) => { resolveReply = resolve }))
    const { container } = render(<SupportChatPanel conversation={{ messages: [] }} onReply={onReply} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'I need assistance' } })
    const form = container.querySelector('form')

    fireEvent.submit(form)
    fireEvent.submit(form)

    expect(onReply).toHaveBeenCalledTimes(1)
    resolveReply()
    await waitFor(() => expect(input.value).toBe(''))
  })

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