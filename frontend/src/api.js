const json = async (path, options = {}) => {
  const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || data.answer || 'Request failed')
  return data
}

export const guestToken = () => localStorage.getItem('nava_guest_token')
export const saveGuestToken = (token) => token && localStorage.setItem('nava_guest_token', token)
export const guestHeaders = () => guestToken() ? { 'X-Guest-Token': guestToken() } : {}
export const getCatalog = (id) => json(`/public/stores/${id}/catalog`)
export const getBusinessTypes = () => json('/business-types')
export const trackOrder = (trackingNumber) => json(`/orders/track/${trackingNumber}`)
export const sendChat = async (id, question) => { const data = await json(`/public/stores/${id}/chat`, { method: 'POST', headers: guestHeaders(), body: JSON.stringify({ question, guest_token: guestToken() }) }); saveGuestToken(data.guest_token); return data }
export const getCart = (id) => json(`/cart/stores/${id}`, { headers: guestHeaders() })
export const checkout = (id, payload) => json(`/orders/stores/${id}`, { method: 'POST', headers: { ...guestHeaders(), 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(payload) })
export const createPayment = (orderId, idempotencyKey) => json(`/payments/orders/${orderId}`, { method: 'POST', headers: { ...guestHeaders(), 'Idempotency-Key': idempotencyKey } })
export const verifyPayment = (paymentId, authority) => json(`/payments/${paymentId}/verify`, { method: 'POST', headers: guestHeaders(), body: JSON.stringify({ authority }) })
export const invoiceUrl = (orderId) => `/orders/${orderId}/invoice`
export const registerUser = (payload) => json('/auth/register', { method: 'POST', body: JSON.stringify(payload) })
export const login = (payload) => json('/auth/login', { method: 'POST', body: JSON.stringify(payload) })
export const getStores = (token) => json('/stores/', { headers: { Authorization: `Bearer ${token}` } })
export const getOrders = (storeId, token) => json(`/seller/orders/stores/${storeId}`, { headers: { Authorization: `Bearer ${token}` } })
export const getConversations = (storeId, token) => json(`/seller/conversations/stores/${storeId}`, { headers: { Authorization: `Bearer ${token}` } })
export const getSellerOrder = (orderId, token) => json(`/seller/orders/${orderId}`, { headers: { Authorization: `Bearer ${token}` } })
export const getConversation = (conversationId, token) => json(`/seller/conversations/${conversationId}`, { headers: { Authorization: `Bearer ${token}` } })
export const updateOrderStatus = (orderId, status, token) => json(`/seller/orders/${orderId}/status`, { method: 'PATCH', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify({ status }) })
export const getProducts = (storeId, token) => json(`/products/?store_id=${storeId}`, { headers: { Authorization: `Bearer ${token}` } })
export const createProduct = (payload, token) => json('/products/', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) })
export const updateProduct = (id, payload, token) => json(`/products/${id}`, { method: 'PUT', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) })
export const deleteProduct = (id, token) => json(`/products/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
export const getKnowledge = (storeId, token) => json(`/stores/${storeId}/knowledge`, { headers: { Authorization: `Bearer ${token}` } })
export const createKnowledge = (storeId, payload, token) => json(`/stores/${storeId}/knowledge`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) })
export const updateKnowledge = (storeId, id, payload, token) => json(`/stores/${storeId}/knowledge/${id}`, { method: 'PUT', headers: { Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) })
export const deleteKnowledge = (storeId, id, token) => json(`/stores/${storeId}/knowledge/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
