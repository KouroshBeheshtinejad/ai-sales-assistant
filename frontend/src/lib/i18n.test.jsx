import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { detectLocale, getBrowserTimezone, I18nProvider, LOCALES, MESSAGES, useI18n } from './i18n'

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

  it('matches newly supported Japanese and falls back for unsupported languages', () => {
    expect(detectLocale({ languages: ['ja-JP'] })).toBe('ja')
    expect(detectLocale({ languages: ['xx-ZZ'] })).toBe('en')
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

  it('localizes a role mismatch from the login API', () => {
    localStorage.setItem('nava_locale', 'fa')
    function Probe() {
      const { err } = useI18n()
      return <p>{err({ message: 'Selected role does not match this account', status: 409 })}</p>
    }
    render(<I18nProvider><Probe /></I18nProvider>)
    expect(screen.getByText('نقش انتخاب‌شده با نقش ثبت‌شده برای این حساب مطابقت ندارد.')).toBeTruthy()
  })

  it('localizes Gmail and phone validation errors returned by the API', () => {
    localStorage.setItem('nava_locale', 'fa')
    function Probe() {
      const { err } = useI18n()
      return <ul>
        <li>{err({ message: 'Email must be a valid Gmail address ending in @gmail.com', status: 422 })}</li>
        <li>{err({ message: 'Phone must include a valid country calling code', status: 422 })}</li>
      </ul>
    }
    render(<I18nProvider><Probe /></I18nProvider>)
    expect(screen.getByText(MESSAGES.fa['auth.gmailOnly'])).toBeTruthy()
    expect(screen.getByText(MESSAGES.fa['auth.phoneInvalid'])).toBeTruthy()
  })
})

describe('store metadata translations', () => {
  const keys = [
    's.contactPhone',
    's.storeAddress',
    's.locationName',
    's.locationUrl',
    's.storeHours',
    's.latitude',
    's.longitude',
  ]
  const englishLabels = [
    'Contact phone',
    'Store address',
    'Location name',
    'Map link',
    'Opening hours',
    'Latitude',
    'Longitude',
  ]
  const sharedInternationalTerms = new Set(['s.latitude', 's.longitude'])

  it.each(LOCALES.filter(({ code }) => code !== 'en'))('%s uses localized store metadata labels', ({ code }) => {
    localStorage.setItem('nava_locale', code)
    function Probe() {
      const { t } = useI18n()
      return <ul>{keys.map((key) => <li key={key}>{t(key)}</li>)}</ul>
    }

    render(<I18nProvider><Probe /></I18nProvider>)
    const labels = screen.getAllByRole('listitem').map((item) => item.textContent)
    expect(labels).toHaveLength(keys.length)
    labels.forEach((label, index) => {
      expect(label).not.toBe(keys[index])
      if (!sharedInternationalTerms.has(keys[index])) expect(label).not.toBe(englishLabels[index])
    })
  })
})

describe('locale catalog completeness', () => {
  const referenceKeys = Object.keys(MESSAGES.en).sort()

  it.each(LOCALES)('%s includes every message and interpolation from English', ({ code }) => {
    const messages = MESSAGES[code]
    expect(Object.keys(messages).sort()).toEqual(referenceKeys)

    for (const key of referenceKeys) {
      const expected = [...MESSAGES.en[key].matchAll(/\{[^}]+\}/g)].map((match) => match[0]).sort()
      const actual = [...messages[key].matchAll(/\{[^}]+\}/g)].map((match) => match[0]).sort()
      expect(actual, `${code}:${key}`).toEqual(expected)
      if (MESSAGES.en[key].trim()) expect(messages[key].trim(), `${code}:${key}`).not.toBe('')
      expect(messages[key], `${code}:${key}`).not.toMatch(/ZXQK|XQZK|PHZX|NAVAPARAM/)
    }
  })

  it('keeps reviewed translations for ambiguous store and payment copy', () => {
    expect(MESSAGES.ar['err.network']).toBe('خطأ في الشبكة. تحقق من اتصالك وحاول مرة أخرى.')
    expect(MESSAGES.ar['shop.storeInfo']).toBe('معلومات المتجر')
    expect(MESSAGES.pt['shop.storeInfo']).toBe('Informações da loja')
    expect(MESSAGES.ar['pay.credentialHint']).toContain('يُشفّر أثناء التخزين')
    expect(MESSAGES.hi['pay.credentialHint']).toContain('संग्रहीत रहते समय एन्क्रिप्ट')
  })

  it.each(LOCALES)('%s does not advertise the retired five-language limit', ({ code }) => {
    const legacyClaim = /\bfive languages?\b|\bcinco idiomas\b|\bfünf sprachen\b|\bcinq langues\b|پنج زبان/i
    for (const key of ['landing.lead', 'landing.b3', 'landing.f7.t']) {
      expect(MESSAGES[code][key], `${code}:${key}`).not.toMatch(legacyClaim)
    }
  })
})