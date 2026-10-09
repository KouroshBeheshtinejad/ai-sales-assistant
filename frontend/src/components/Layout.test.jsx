import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { LocaleToggle, SiteFooter, SiteHeader } from './Layout'

const authState = vi.hoisted(() => ({ isAuthed: false, user: null }))

vi.mock('../lib/auth', () => ({ useAuth: () => ({ isAuthed: authState.isAuthed, user: authState.user }) }))
vi.mock('../lib/i18n', () => ({
  useI18n: () => ({
    t: (key) => key,
    locale: 'en',
    setLocale: vi.fn(),
    locales: [
      { code: 'en', name: 'English', short: 'EN', country: 'US', dir: 'ltr' },
      { code: 'it', name: 'Italiano', short: 'IT', country: 'IT', dir: 'ltr' },
    ],
    meta: { tag: 'en' },
  }),
}))
vi.mock('./ui', () => ({
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
  Icon: () => <span aria-hidden="true" />,
}))

afterEach(() => { cleanup(); authState.isAuthed = false; authState.user = null })

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

  it('shows the signed-in user name in the public header', () => {
    authState.isAuthed = true
    authState.user = { first_name: 'Sara', last_name: 'Nava', email: 'sara@example.com' }

    render(<MemoryRouter><SiteHeader /></MemoryRouter>)

    expect(screen.getByText('Sara Nava')).toBeTruthy()
  })

  it('shows country flags beside language choices', () => {
    render(<MemoryRouter><LocaleToggle /></MemoryRouter>)

    fireEvent.click(screen.getByRole('button', { name: 'nav.langName' }))

    const italianOption = screen.getByRole('option', { name: /IT Italiano/ })
    expect(italianOption.querySelector('.locale-flag').textContent).toBe('🇮🇹')
    expect(document.querySelector('.lang-button .locale-flag').textContent).toBe('🇺🇸')
  })
})