// Guest identity. The backend scopes a guest token to ONE store (it is the token
// of a Conversation), so it is stored per store. The key matches the server-rendered
// /public/stores/{id} page, so both pages share the same cart.
import { safeStorage } from './util'

const key = (storeId) => `nava_guest_token_${storeId}`
export const getGuest = (storeId) => safeStorage.get(key(storeId))
export const setGuest = (storeId, token) => safeStorage.set(key(storeId), token)
export const clearGuest = (storeId) => safeStorage.remove(key(storeId))
