import { clearToken, getToken } from './session'

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message)
    this.status = status
    this.data = data
  }
}

// FastAPI returns `detail` as a string, or as a list of validation errors (422).
function messageFrom(data) {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => String(item.msg || '').replace(/^Value error, /, '')).filter(Boolean).join(' / ')
  }
  if (typeof data?.answer === 'string') return data.answer // chat errors
  return ''
}

async function request(path, { method = 'GET', body, auth = false, guest, headers, blob = false } = {}) {
  const requestHeaders = { Accept: blob ? 'application/pdf' : 'application/json', ...headers }
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && !isFormData) requestHeaders['Content-Type'] = 'application/json'
  if (guest) requestHeaders['X-Guest-Token'] = guest
  if (auth) {
    const token = getToken()
    if (token) requestHeaders.Authorization = `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(path, { method, headers: requestHeaders, body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body) })
  } catch {
    throw new ApiError('Network error', 0)
  }
  if (response.ok && blob) return response.blob()

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && auth) clearToken() // expired / revoked session
    throw new ApiError(messageFrom(data) || `HTTP ${response.status}`, response.status, data)
  }
  return data
}

const seller = (path, options) => request(path, { auth: true, ...options })

export const api = {
  // Public
  businessTypes: () => request('/business-types'),
  catalog: (storeId) => request(`/public/stores/${storeId}/catalog`),
  chat: (storeId, question, guest) =>
    request(`/public/stores/${storeId}/chat`, { method: 'POST', guest, body: { question, guest_token: guest || undefined } }),
  track: (number) => request(`/orders/track/${encodeURIComponent(number)}`),

  // Guest cart / orders / payments
  cart: {
    get: (storeId, guest) => request(`/cart/stores/${storeId}`, { guest }),
    add: (storeId, productId, quantity, guest) =>
      request(`/cart/stores/${storeId}/items`, { method: 'POST', guest, body: { product_id: productId, quantity } }),
    update: (storeId, productId, quantity, guest) =>
      request(`/cart/stores/${storeId}/items/${productId}`, { method: 'PATCH', guest, body: { quantity } }),
    remove: (storeId, productId, guest) => request(`/cart/stores/${storeId}/items/${productId}`, { method: 'DELETE', guest }),
    clear: (storeId, guest) => request(`/cart/stores/${storeId}`, { method: 'DELETE', guest }),
  },
  checkout: (storeId, payload, guest, idempotencyKey) =>
    request(`/orders/stores/${storeId}`, { method: 'POST', guest, body: payload, headers: { 'Idempotency-Key': idempotencyKey } }),
  guestInvoice: (storeId, orderId, guest) => request(`/orders/stores/${storeId}/guest/${orderId}/invoice`, { guest, blob: true }),
  pay: (orderId, idempotencyKey, guest) =>
    request(`/payments/orders/${orderId}`, { method: 'POST', guest, headers: { 'Idempotency-Key': idempotencyKey } }),
  verifyPayment: (paymentId, authority, guest) =>
    request(`/payments/${paymentId}/verify`, { method: 'POST', guest, body: { authority } }),

  // Auth
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  verify: (payload) => request('/auth/verify', { method: 'POST', body: payload }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  requestReset: (email) => request('/auth/password-reset/request', { method: 'POST', body: { email } }),
  confirmReset: (token, newPassword) =>
    request('/auth/password-reset/confirm', { method: 'POST', body: { token, new_password: newPassword } }),

  // Seller (Bearer token)
  seller: {
    stores: () => seller('/stores/'),
    createStore: (payload) => seller('/stores/', { method: 'POST', body: payload }),
    updateStore: (id, payload) => seller(`/stores/${id}`, { method: 'PUT', body: payload }),
    uploadStoreLogo: (id, file) => {
      const body = new FormData()
      body.append('logo', file)
      return seller(`/stores/${id}/logo`, { method: 'POST', body })
    },
    deleteStore: (id) => seller(`/stores/${id}`, { method: 'DELETE' }),

    orders: (storeId) => seller(`/seller/orders/stores/${storeId}`),
    order: (id) => seller(`/seller/orders/${id}`),
    setOrderStatus: (id, status) => seller(`/seller/orders/${id}/status`, { method: 'PATCH', body: { status } }),

    conversations: (storeId) => seller(`/seller/conversations/stores/${storeId}`),
    conversation: (id) => seller(`/seller/conversations/${id}`),

    products: (storeId) => seller(`/products/?store_id=${storeId}`),
    createProduct: (payload) => seller('/products/', { method: 'POST', body: payload }),
    updateProduct: (id, payload) => seller(`/products/${id}`, { method: 'PUT', body: payload }),
    uploadProductImage: (id, file) => {
      const body = new FormData()
      body.append('image', file)
      return seller(`/products/${id}/image`, { method: 'POST', body })
    },
    deleteProduct: (id) => seller(`/products/${id}`, { method: 'DELETE' }),

    list: (storeId, kind) => seller(`/stores/${storeId}/${kind}`), // kind: 'knowledge' | 'faqs'
    create: (storeId, kind, payload) => seller(`/stores/${storeId}/${kind}`, { method: 'POST', body: payload }),
    update: (storeId, kind, id, payload) => seller(`/stores/${storeId}/${kind}/${id}`, { method: 'PUT', body: payload }),
    remove: (storeId, kind, id) => seller(`/stores/${storeId}/${kind}/${id}`, { method: 'DELETE' }),
  },
}
