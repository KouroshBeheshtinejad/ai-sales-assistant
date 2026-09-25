import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import de from './locales/de'
import en from './locales/en'
import es from './locales/es'
import fa from './locales/fa'
import fr from './locales/fr'
import { LISTS } from './locales/lists'
import { safeStorage, toLatinDigits } from './util'

// One entry per supported language. `unit` is the currency word used next to prices
// (the catalogue is priced in Toman, see the server-rendered store page).
export const LOCALES = [
  { code: 'fa', name: 'فارسی', short: 'FA', dir: 'rtl', tag: 'fa-IR', unit: 'تومان' },
  { code: 'en', name: 'English', short: 'EN', dir: 'ltr', tag: 'en-US', unit: 'Toman' },
  { code: 'es', name: 'Español', short: 'ES', dir: 'ltr', tag: 'es-ES', unit: 'tomanes' },
  { code: 'de', name: 'Deutsch', short: 'DE', dir: 'ltr', tag: 'de-DE', unit: 'Toman' },
  { code: 'fr', name: 'Français', short: 'FR', dir: 'ltr', tag: 'fr-FR', unit: 'tomans' },
]

export const DEFAULT_LOCALE = 'fa'
const STORAGE_KEY = 'nava_locale'
const MESSAGES = { fa, en, es, de, fr }
const byCode = (code) => LOCALES.find((item) => item.code === code)

const storedLocale = () => {
  const value = safeStorage.get(STORAGE_KEY)
  return byCode(value) ? value : DEFAULT_LOCALE
}

// Sets <html lang dir> straight away (module load, before React renders) so a stored
// non-Persian choice never flashes a right-to-left page first.
function applyDocument(code) {
  const meta = byCode(code) || byCode(DEFAULT_LOCALE)
  const root = document.documentElement
  if (root.lang !== meta.code) root.lang = meta.code
  if (root.dir !== meta.dir) root.dir = meta.dir
}
if (typeof document !== 'undefined') applyDocument(storedLocale())

const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
const humanize = (name) => String(name).replace(/[_-]+/g, ' ').replace(/^./, (c) => c.toUpperCase())

// Maps the English messages the API sends (FastAPI `detail`) to translation keys.
const SERVER_MESSAGES = [
  [/invalid email or password/i, 'err.m.invalidCredentials'],
  [/email already registered/i, 'err.m.emailTaken'],
  [/invalid or expired verification code/i, 'err.m.invalidCode'],
  [/invalid or expired reset token/i, 'err.m.invalidReset'],
  [/verification is required/i, 'err.m.needVerify'],
  [/session expired/i, 'err.m.sessionExpired'],
  [/insufficient stock/i, 'err.m.stock'],
  [/cart is empty/i, 'err.m.cartEmpty'],
  [/product is not (active|available)/i, 'err.m.inactive'],
  [/quantity must be between/i, 'err.m.qty'],
  [/unsupported image|image is too large|invalid image|image dimensions|image is empty/i, 'err.m.image'],
  [/already paid/i, 'err.m.paid'],
  [/only pending orders/i, 'err.m.notPending'],
  [/guest token/i, 'err.m.guest'],
]

function createTranslator(code) {
  const meta = byCode(code) || byCode(DEFAULT_LOCALE)
  const messages = MESSAGES[meta.code]
  const lists = LISTS[meta.code] || { biz: {}, field: {}, option: {} }
  const plural = new Intl.PluralRules(meta.tag)
  const numberFormat = new Intl.NumberFormat(meta.tag)
  const moneyFormat = new Intl.NumberFormat(meta.tag, { maximumFractionDigits: 2 })
  const dateFormat = new Intl.DateTimeFormat(meta.tag, { dateStyle: 'medium', timeStyle: 'short' })

  const num = (value) => {
    const n = Number(toLatinDigits(String(value ?? '')).replace(/[,٬\s]/g, ''))
    return Number.isFinite(n) && value !== '' && value != null ? numberFormat.format(n) : String(value ?? '')
  }
  // Identifiers (order and tracking numbers): digits are localised but never grouped.
  const id = (value) => {
    const text = String(value ?? '')
    return meta.code === 'fa' ? text.replace(/\d/g, (d) => FA_DIGITS[d]) : text
  }
  const money = (value) => `${moneyFormat.format(Number(value) || 0)} ${meta.unit}`
  const date = (value) => (value instanceof Date && !Number.isNaN(value.getTime()) ? dateFormat.format(value) : '')

  const t = (key, params) => {
    let text
    const count = params && params.n != null ? Number(toLatinDigits(String(params.n)).replace(/[,٬\s]/g, '')) : null
    if (count !== null && Number.isFinite(count)) {
      const form = plural.select(count)
      text = messages[`${key}_${form}`] ?? messages[key] ?? en[`${key}_${form}`] ?? en[key]
    } else {
      text = messages[key] ?? en[key]
    }
    if (text === undefined) return key
    if (!params) return text
    return text.replace(/\{(\w+)\}/g, (whole, name) => {
      if (!(name in params)) return whole
      const value = params[name]
      return typeof value === 'number' ? numberFormat.format(value) : String(value)
    })
  }

  const err = (error) => {
    const raw = typeof error === 'string' ? error : error?.message || ''
    const status = error?.status
    if (status === 0) return t('err.network')
    for (const [pattern, key] of SERVER_MESSAGES) if (pattern.test(raw)) return t(key)
    if (status === 429) return t('err.rate')
    if (status === 401) return t('err.auth')
    if (status === 404) return t('err.notFound')
    if (status >= 500) return t('err.server')
    return raw && !/^HTTP \d+$/.test(raw) ? raw : t('err.generic')
  }

  return {
    locale: meta.code,
    meta,
    t,
    num,
    id,
    money,
    date,
    err,
    bizLabel: (slug, fallback) => lists.biz[slug] || fallback || humanize(slug),
    fieldLabel: (field) => lists.field[field.name] || field.label || humanize(field.name),
    optionLabel: (value) => lists.option[value] || value,
  }
}

const I18nContext = createContext(null)

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(storedLocale)
  const value = useMemo(() => ({ ...createTranslator(locale), locales: LOCALES }), [locale])

  useEffect(() => { applyDocument(locale) }, [locale])

  const setLocale = (code) => {
    if (!byCode(code)) return
    safeStorage.set(STORAGE_KEY, code)
    setLocaleState(code)
  }
  const context = useMemo(() => ({ ...value, setLocale }), [value]) // eslint-disable-line react-hooks/exhaustive-deps
  return <I18nContext.Provider value={context}>{children}</I18nContext.Provider>
}

export const useI18n = () => useContext(I18nContext)