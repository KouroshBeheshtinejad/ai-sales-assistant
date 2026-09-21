export const cx = (...parts) => parts.filter(Boolean).join(' ')

export function uuid() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
}

const FA = '۰۱۲۳۴۵۶۷۸۹'
const AR = '٠١٢٣٤٥٦٧٨٩'
// Persian keyboards produce ۱۲۳ / ١٢٣; the backend matches ASCII digits.
export const toLatinDigits = (value = '') =>
  String(value).replace(/[۰-۹٠-٩]/g, (d) => String(FA.includes(d) ? FA.indexOf(d) : AR.indexOf(d)))

// The API returns naive UTC timestamps ("2026-01-01T10:00:00"); without a zone
// the browser would read them as local time.
export function parseDate(value) {
  if (!value) return null
  const text = String(value)
  return new Date(/([zZ]|[+-]\d\d:?\d\d)$/.test(text) ? text : `${text}Z`)
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

export function safeNext(value) {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/seller'
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = Object.assign(document.createElement('a'), { href: url, download: filename })
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}

export const safeStorage = {
  get: (key) => { try { return localStorage.getItem(key) } catch { return null } },
  set: (key, value) => { try { localStorage.setItem(key, value) } catch { /* private mode */ } },
  remove: (key) => { try { localStorage.removeItem(key) } catch { /* private mode */ } },
}
