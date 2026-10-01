import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { detectLocale, getBrowserTimezone, I18nProvider, useI18n } from './i18n'

afterEach(() => {
  cleanup()
  localStorage.clear()
})

describe('automatic visitor language selection', () => {
  it('prioritizes explicit choice over saved preference and browser language', () => {
    expect(detectLocale({ explicit: 'fr', stored: 'de', languages: ['fa-IR'] })).toBe('fr')
  })

  it('uses saved preference before browser language', () => {
    expect(detectLocale({ stored: 'de', languages: ['fa-IR'] })).toBe('de')
  })

  it.each([
    ['fa-IR', 'fa'],
    ['en-US', 'en'],
    ['es-MX', 'es'],
    ['de-AT', 'de'],
    ['fr-CA', 'fr'],
  ])('matches browser language %s to %s', (browserLanguage, expected) => {
    expect(detectLocale({ languages: [browserLanguage] })).toBe(expected)
  })

  it('falls back to English for unsupported browser languages', () => {
    expect(detectLocale({ languages: ['ja-JP'] })).toBe('en')
    expect(detectLocale({ languages: [] })).toBe('en')
  })

  it('uses the device timezone and falls back to UTC when unavailable', () => {
    vi.spyOn(Intl, 'DateTimeFormat').mockImplementationOnce(() => ({
      resolvedOptions: () => ({ timeZone: 'Europe/Paris' }),
    }))
    expect(getBrowserTimezone()).toBe('Europe/Paris')

    vi.spyOn(Intl, 'DateTimeFormat').mockImplementationOnce(() => {
      throw new Error('Timezone unavailable')
    })
    expect(getBrowserTimezone()).toBe('UTC')
    vi.restoreAllMocks()
  })

  it('persists manual selection and updates document language and direction', () => {
    function Probe() {
      const { locale, setLocale } = useI18n()
      return <button onClick={() => setLocale('fa')}>{locale}</button>
    }
    localStorage.setItem('nava_locale', 'en')
    render(<I18nProvider><Probe /></I18nProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'en' }))
    expect(localStorage.getItem('nava_locale')).toBe('fa')
    expect(localStorage.getItem('nava_locale_explicit')).toBe('fa')
    expect(document.documentElement.dir).toBe('rtl')
    expect(document.documentElement.lang).toBe('fa')
  })
})