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
