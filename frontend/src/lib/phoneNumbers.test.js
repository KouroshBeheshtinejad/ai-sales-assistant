import { describe, expect, it } from 'vitest'
import { flagEmoji, normalizePhoneNumber, phoneCountries, splitPhoneNumber } from './phoneNumbers'

describe('international phone helpers', () => {
  it('renders ISO country flag indicators', () => {
    expect(flagEmoji('IT')).toBe('🇮🇹')
    expect(flagEmoji('not-a-country')).toBe('')
  })

  it('lists localized countries with their calling codes', () => {
    const countries = phoneCountries('en')
    expect(countries.length).toBeGreaterThan(200)
    expect(countries.find((item) => item.country === 'IR').callingCode).toBe('98')
  })

  it('validates and normalizes national numbers to E.164', () => {
    expect(normalizePhoneNumber('09123456789', 'IR')).toBe('+989123456789')
    expect(normalizePhoneNumber('12', 'IR')).toBeNull()
    expect(normalizePhoneNumber('', 'IR')).toBe('')
  })

  it('splits previously stored international numbers for editing', () => {
    expect(splitPhoneNumber('+989123456789')).toEqual({ country: 'IR', nationalNumber: '9123456789' })
  })
})