import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { clearToken, getToken, isTokenValid, setToken, subscribe, tokenExpiry } from './session'
import { api } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const stored = useSyncExternalStore(subscribe, getToken)
  const token = isTokenValid(stored) ? stored : null
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(token))

  useEffect(() => {
    let current = true
    if (!token) {
      setUser(null)
      setLoading(false)
      return () => { current = false }
    }
    setLoading(true)
    api.me()
      .then((profile) => { if (current) setUser(profile) })
      .catch(() => { if (current) { setUser(null); clearToken() } })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [token])

  useEffect(() => {
    if (stored && !token) { clearToken(); return undefined }
    const expiry = token && tokenExpiry(token)
    if (!expiry) return undefined
    const timer = setTimeout(clearToken, Math.max(0, expiry - Date.now()))
    return () => clearTimeout(timer)
  }, [stored, token])

  const authLoading = Boolean(token) && (loading || !user)
  const value = useMemo(() => ({ token, user, loading: authLoading, isAuthed: Boolean(token), signIn: setToken, signOut: clearToken }), [token, user, authLoading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

export function RequireAuth({ children }) {
  const { isAuthed, loading } = useAuth()
  const location = useLocation()
  if (loading) return null
  if (!isAuthed) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  return children
}

export function RequireRoles({ roles, children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user || !roles.includes(user.role) || user.approval_status !== 'active') return <Navigate to="/workspace" replace />
  return children
}
