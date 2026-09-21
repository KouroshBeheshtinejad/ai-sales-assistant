import { createContext, useContext, useState } from 'react'
import { api } from '../../lib/api'
import { useAsync, useBusinessTypes } from '../../lib/hooks'
import { safeStorage } from '../../lib/util'

const ACTIVE_KEY = 'nava_active_store_id'
const SellerContext = createContext(null)
export const useSeller = () => useContext(SellerContext)

// Loads the seller's stores once and tracks which one every page is working on.
export function SellerProvider({ children }) {
  const result = useAsync(() => api.seller.stores(), [])
  const types = useBusinessTypes()
  const [activeId, setActiveId] = useState(() => safeStorage.get(ACTIVE_KEY))
  const stores = result.data || []
  const store = stores.find((s) => String(s.id) === String(activeId)) || stores[0] || null

  const select = (id) => { safeStorage.set(ACTIVE_KEY, String(id)); setActiveId(String(id)) }
  const value = {
    stores,
    store,
    select,
    types,
    businessType: types.find((x) => x.slug === store?.business_type) || null,
    reloadStores: result.reload,
    loading: result.loading && !result.data,
    error: result.error,
  }
  return <SellerContext.Provider value={value}>{children}</SellerContext.Provider>
}
