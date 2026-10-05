import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'

// Runs `fn` whenever `deps` change; `fn` may return null to skip.
export function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const ticket = useRef(0)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(async () => {
    const mine = ++ticket.current
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fn()
      if (mine === ticket.current) setState({ data, error: null, loading: false })
    } catch (error) {
      if (mine === ticket.current) setState({ data: null, error, loading: false })
    }
  }, deps)
  useEffect(() => { run(); return () => { ticket.current++ } }, [run])
  return { ...state, reload: run, setData: (data) => setState((s) => ({ ...s, data })) }
}

let businessTypesPromise
export function useBusinessTypes() {
  const [types, setTypes] = useState([])
  useEffect(() => {
    businessTypesPromise ||= api.businessTypes().catch((error) => { businessTypesPromise = null; throw error })
    businessTypesPromise.then(setTypes).catch(() => {})
  }, [])
  return types
}

export function useSeo({ title, description }) {
  useEffect(() => {
    if (title) document.title = title
    const setMeta = (selector, attr, value) => {
      const node = document.head.querySelector(selector)
      if (node && value) node.setAttribute(attr, value)
    }
    setMeta('meta[name="description"]', 'content', description)
    setMeta('meta[property="og:title"]', 'content', title)
    setMeta('meta[property="og:description"]', 'content', description)
  }, [title, description])
}

// Random stores and products for the landing page. `shuffle()` asks for a new sample.
export function useShowcase(stores = 6, products = 8) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [round, setRound] = useState(0)
  useEffect(() => {
    let live = true
    setState((current) => ({ ...current, loading: true }))
    api.showcase(stores, products)
      .then((data) => { if (live) setState({ data, error: null, loading: false }) })
      .catch((error) => { if (live) setState((current) => ({ data: current.data, error, loading: false })) })
    return () => { live = false }
  }, [stores, products, round])
  return { ...state, shuffle: () => setRound((n) => n + 1) }
}

export function useHomeSections() {
  const [state, setState] = useState({ sections: [], loading: true })
  useEffect(() => {
    let live = true
    api.homeSections()
      .then((data) => { if (live) setState({ sections: Array.isArray(data?.sections) ? data.sections : [], loading: false }) })
      .catch(() => { if (live) setState({ sections: [], loading: false }) })
    return () => { live = false }
  }, [])
  return state
}

// The small "type the number you see" human check used on login, registration, and
// the seller account form. A challenge is single-use: get a fresh one after every
// submit attempt (successful or not), never reuse a solved/failed token.
export function useCaptcha() {
  const [token, setToken] = useState(null)
  const [image, setImage] = useState(null)
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(true)
  const ticket = useRef(0)

  const refresh = useCallback(() => {
    const mine = ++ticket.current
    setLoading(true)
    setAnswer('')
    api.captcha()
      .then((data) => { if (mine === ticket.current) { setToken(data.captcha_token); setImage(data.image); setLoading(false) } })
      .catch(() => { if (mine === ticket.current) setLoading(false) })
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { token, image, answer, setAnswer, loading, refresh }
}
