import { getCountries, getCountryCallingCode, parsePhoneNumberFromString } from 'libphonenumber-js/min'
import { toLatinDigits } from './util'

const countryCache = new Map()

export function phoneCountries(locale) {
  if (!countryCache.has(locale)) {
    const names = new Intl.DisplayNames([locale], { type: 'region' })
    const options = getCountries().map((country) => ({
      country,
      callingCode: getCountryCallingCode(country),
      name: names.of(country) || country,
    })).sort((a, b) => a.name.localeCompare(b.name, locale))
    countryCache.set(locale, options)
  }
  return countryCache.get(locale)
}

export function normalizePhoneNumber(value, country) {
  if (!String(value || '').trim()) return ''
  const parsed = parsePhoneNumberFromString(toLatinDigits(String(value).trim()), country)
  return parsed?.isValid() ? parsed.number : null
}

export function splitPhoneNumber(value, defaultCountry = 'IR') {
  const input = String(value || '').trim()
  if (!input) return { country: defaultCountry, nationalNumber: '' }
  const parsed = parsePhoneNumberFromString(input, defaultCountry)
  if (!parsed) return { country: defaultCountry, nationalNumber: input }
  return { country: parsed.country || defaultCountry, nationalNumber: parsed.nationalNumber || input }
}