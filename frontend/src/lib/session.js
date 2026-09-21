// Seller session: JWT kept in localStorage (the API only accepts Bearer tokens).
import { safeStorage } from './util'

const KEY = 'nava_seller_token'
const listeners = new Set()
const emit = () => listeners.forEach((fn) => fn())

export const getToken = () => safeStorage.get(KEY)

export function subscribe(fn) {
  listeners.add(fn)
  window.addEventListener('storage', fn)
  return () => {
    listeners.delete(fn)
    window.removeEventListener('storage', fn)
  }
}

export function setToken(token) { safeStorage.set(KEY, token); emit() }
export function clearToken() { safeStorage.remove(KEY); emit() }

export function tokenExpiry(token) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { exp } = JSON.parse(atob(payload))
    return exp ? exp * 1000 : null
  } catch {
    return null
  }
}

export function isTokenValid(token) {
  if (!token) return false
  const exp = tokenExpiry(token)
  return !exp || exp > Date.now()
}
