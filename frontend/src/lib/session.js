// The access token is HttpOnly cookie state. Only an in-memory session marker is kept.
const COOKIE_SESSION = 'cookie-session'
let active = false
const listeners = new Set()
const emit = () => listeners.forEach((fn) => fn())

export const getToken = () => active ? COOKIE_SESSION : null

export function subscribe(fn) {
  listeners.add(fn)
  window.addEventListener('storage', fn)
  return () => {
    listeners.delete(fn)
    window.removeEventListener('storage', fn)
  }
}

export function setToken() { active = true; emit() }
export function clearToken() { active = false; emit() }

export function tokenExpiry(token) {
  if (token === COOKIE_SESSION) return null
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
