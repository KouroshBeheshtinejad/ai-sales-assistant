import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from './api'
import { clearGuest, getGuest, setGuest } from './guest'

// The backend only hands out a guest token by opening a conversation through the
// chat endpoint. "View cart" is matched by a deterministic intent, so this request
// creates the session without ever calling the language model.
const SESSION_BOOTSTRAP = 'سبد خرید من'

export function useShop(storeId) {
  const [catalog, setCatalog] = useState(null)
  const [error, setError] = useState(null)
  const [cart, setCart] = useState(null)
  const guest = useRef(null)
  const pending = useRef(null)

  const reloadCatalog = useCallback(() => {
    setError(null)
    return api.catalog(storeId).then(setCatalog).catch(setError)
  }, [storeId])

  const dropGuest = useCallback(() => {
    clearGuest(storeId)
    guest.current = null
    setCart(null)
  }, [storeId])

  const refreshCart = useCallback(async () => {
    if (!guest.current) return null
    try {
      const next = await api.cart.get(storeId, guest.current)
      setCart(next)
      return next
    } catch (e) {
      if (e.status === 401 || e.status === 404) dropGuest()
      return null
    }
  }, [storeId, dropGuest])

  useEffect(() => {
    setCatalog(null)
    setError(null)
    setCart(null)
    pending.current = null
    guest.current = getGuest(storeId)
    reloadCatalog()
    refreshCart()
  }, [storeId, reloadCatalog, refreshCart])

  const remember = useCallback((token) => {
    if (token && token !== guest.current) {
      guest.current = token
      setGuest(storeId, token)
    }
  }, [storeId])

  const ensureGuest = useCallback(() => {
    if (guest.current) return Promise.resolve(guest.current)
    pending.current ||= api.chat(storeId, SESSION_BOOTSTRAP, null)
      .then((res) => {
        remember(res.guest_token)
        if (!guest.current) throw new ApiError('Guest token is required', 401)
        return guest.current
      })
      .finally(() => { pending.current = null })
    return pending.current
  }, [storeId, remember])

  // Runs a cart mutation; if the stored token is stale, opens a fresh session once.
  const mutate = useCallback(async (run) => {
    for (let attempt = 0; ; attempt += 1) {
      const token = await ensureGuest()
      try {
        const next = await run(token)
        setCart(next)
        return next
      } catch (e) {
        if (attempt === 0 && /guest token/i.test(e.message)) { dropGuest(); continue }
        throw e
      }
    }
  }, [ensureGuest, dropGuest])

  return {
    storeId,
    catalog,
    error,
    cart,
    cartCount: cart ? cart.items.reduce((sum, item) => sum + item.quantity, 0) : 0,
    reloadCatalog,
    refreshCart,
    getGuestToken: () => guest.current,
    ensureGuest,
    remember,
    addToCart: (productId, quantity = 1) => mutate((g) => api.cart.add(storeId, productId, quantity, g)),
    setQuantity: (productId, quantity) => mutate((g) => api.cart.update(storeId, productId, quantity, g)),
    removeItem: (productId) => mutate((g) => api.cart.remove(storeId, productId, g)),
    clearCart: () => mutate((g) => api.cart.clear(storeId, g)),
  }
}
