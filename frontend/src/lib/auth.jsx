import { createContext, useContext, useEffect, useMemo, useSyncExternalStore } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { clearToken, getToken, isTokenValid, setToken, subscribe, tokenExpiry } from './session'
import { api } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const stored = useSyncExternalStore(subscribe, getToken)
  const token = isTokenValid(stored) ? stored : null

  useEffect(() => {
    api.me().then(() => setToken()).catch(() => clearToken())
  }, [])

  useEffect(() => {
    if (stored && !token) { clearToken(); return undefined }
    const expiry = token && tokenExpiry(token)
    if (!expiry) return undefined
    const timer = setTimeout(clearToken, Math.max(0, expiry - Date.now()))
    return () => clearTimeout(timer)
  }, [stored, token])

  const value = useMemo(() => ({ token, isAuthed: Boolean(token), signIn: setToken, signOut: clearToken }), [token])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

export function RequireAuth({ children }) {
  const { isAuthed } = useAuth()
  const location = useLocation()
  if (!isAuthed) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  return children
}
