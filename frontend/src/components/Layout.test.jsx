import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { SiteFooter, SiteHeader } from './Layout'

vi.mock('../lib/auth', () => ({ useAuth: () => ({ isAuthed: false }) }))
vi.mock('../lib/i18n', () => ({
  useI18n: () => ({
    t: (key) => key,
    locale: 'en',
    setLocale: vi.fn(),
    locales: [{ code: 'en', name: 'English' }],
    meta: { tag: 'en' },
  }),
}))
vi.mock('./ui', () => ({
  Button: ({ children }) => <button>{children}</button>,
  Icon: () => <span aria-hidden="true" />,
}))

afterEach(() => cleanup())

describe('site navigation', () => {
  it('keeps features and how-it-works links in the footer, not the header', () => {
    render(<MemoryRouter><><SiteHeader /><SiteFooter /></></MemoryRouter>)

    const header = screen.getByRole('banner')
    const footer = screen.getByRole('contentinfo')
    expect(within(header).queryByText('nav.features')).toBeNull()
    expect(within(header).queryByText('nav.how')).toBeNull()
    expect(within(footer).getByText('nav.features')).toBeTruthy()
    expect(within(footer).getByText('nav.how')).toBeTruthy()
  })
})