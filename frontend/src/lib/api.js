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
  const apiPath = path.startsWith('/api/') ? path : `/api${path}`
  const requestHeaders = { Accept: blob ? 'application/pdf' : 'application/json', ...headers }
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && !isFormData) requestHeaders['Content-Type'] = 'application/json'
  if (guest) requestHeaders['X-Guest-Token'] = guest
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())) {
    const csrfToken = document.cookie.split('; ').find((item) => item.startsWith('csrf_token='))?.split('=').slice(1).join('=')
    if (csrfToken) requestHeaders['X-CSRF-Token'] = decodeURIComponent(csrfToken)
  }
  if (auth) {
    const token = getToken()
    if (token && token !== 'cookie-session') requestHeaders.Authorization = `Bearer ${token}`
  }

  let response
  try {
    response = await fetch(apiPath, { method, headers: requestHeaders, body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body) })
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
  // Random live stores and products for the landing page.
  showcase: (stores = 6, products = 8) => request(`/public/showcase?stores=${stores}&products=${products}`),
  homeSections: () => request('/public/home-sections'),
  storesByBusinessType: (businessType, limit = 100) => request(`/public/stores?business_type=${encodeURIComponent(businessType)}&limit=${limit}`),
  chat: (storeId, question, guest) =>
    request(`/public/stores/${storeId}/chat`, { method: 'POST', guest, body: { question, guest_token: guest || undefined } }),
  track: (number) => request(`/orders/track/${encodeURIComponent(number)}`),
  trackInvoice: (number, locale, timezone) => request(
    `/orders/track/${encodeURIComponent(number)}/invoice?locale=${encodeURIComponent(locale)}&timezone=${encodeURIComponent(timezone)}`,
    { blob: true },
  ),

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
  guestOrder: (storeId, orderId, guest) => request(`/orders/stores/${storeId}/guest/${orderId}`, { guest }),
  guestInvoice: (storeId, orderId, guest, locale, timezone) =>
    request(`/orders/stores/${storeId}/guest/${orderId}/invoice?locale=${encodeURIComponent(locale)}&timezone=${encodeURIComponent(timezone)}`, { guest, blob: true }),
  pay: (orderId, idempotencyKey, guest) =>
    request(`/payments/orders/${orderId}`, { method: 'POST', guest, headers: { 'Idempotency-Key': idempotencyKey } }),
  verifyPayment: (paymentId, authority, guest) =>
    request(`/payments/${paymentId}/verify`, { method: 'POST', guest, body: { authority } }),

  // Auth
  captcha: () => request('/captcha'),
  register: (payload) => request('/auth/register', { method: 'POST', body: payload }),
  verify: (payload) => request('/auth/verify', { method: 'POST', body: payload }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
  me: () => request('/auth/me', { auth: true }),
  orders: () => seller('/orders'),
  invoice: (orderId, locale, timezone) => seller(
    `/orders/${orderId}/invoice?locale=${encodeURIComponent(locale)}&timezone=${encodeURIComponent(timezone)}`,
    { blob: true },
  ),
  updateProfile: (payload) => request('/auth/me', { method: 'PATCH', auth: true, body: payload }),
  requestReset: (email) => request('/auth/password-reset/request', { method: 'POST', body: { email } }),
  confirmReset: (token, newPassword) =>
    request('/auth/password-reset/confirm', { method: 'POST', body: { token, new_password: newPassword } }),

  admin: {
    users: () => seller('/admin/users'),
    setRole: (userId, role) => seller(`/admin/users/${userId}/role`, { method: 'PATCH', body: { role } }),
    decideAccount: (userId, status) => seller(`/admin/users/${userId}/approval`, { method: 'PATCH', body: { status } }),
    stores: () => seller('/admin/stores'),
    transferStoreOwner: (storeId, userId) => seller(`/admin/stores/${storeId}/owner`, { method: 'PATCH', body: { user_id: userId } }),
    products: () => seller('/admin/products'),
    orders: () => seller('/admin/orders'),
    auditLogs: () => seller('/admin/audit-logs'),
    databaseSummary: () => seller('/admin/database/summary'),
    systemOverview: () => seller('/admin/system/overview'),
    databaseRecords: (entity, query = '') => seller(`/admin/database/${encodeURIComponent(entity)}?q=${encodeURIComponent(query)}`),
    databaseRecord: (entity, id) => seller(`/admin/database/${encodeURIComponent(entity)}/${id}`),
    homeSections: {
      list: () => seller('/admin/home-sections'),
      create: (payload) => seller('/admin/home-sections', { method: 'POST', body: payload }),
      update: (id, payload) => seller(`/admin/home-sections/${id}`, { method: 'PATCH', body: payload }),
      remove: (id) => seller(`/admin/home-sections/${id}`, { method: 'DELETE' }),
      reorder: (ids) => seller('/admin/home-sections/order', { method: 'PUT', body: { ids } }),
      preview: (id) => seller(`/admin/home-sections/${id}/preview`),
    },
  },

  support: {
    summary: () => seller('/support/summary'),
    stores: (query = '') => seller(`/support/stores?q=${encodeURIComponent(query)}`),
    create: (payload) => seller('/support/conversations', { method: 'POST', body: payload }),
    conversations: () => seller('/support/conversations'),
    conversation: (id) => seller(`/support/conversations/${id}`),
    reply: (id, message) => seller(`/support/conversations/${id}/reply`, { method: 'POST', body: { message } }),
    queue: (status) => seller(`/support/queue${status ? `?status_filter=${encodeURIComponent(status)}` : ''}`),
    claim: (id) => seller(`/support/queue/${id}/claim`, { method: 'POST' }),
    agentReply: (id, message) => seller(`/support/queue/${id}/reply`, { method: 'POST', body: { message } }),
    setStatus: (id, status) => seller(`/support/queue/${id}/status`, { method: 'PATCH', body: { status } }),
  },

  // Seller (Bearer token)
  seller: {
    stores: () => seller('/stores/'),
    paymentSettings: (storeId) => seller(`/stores/${storeId}/payment-settings`),
    updatePaymentSettings: (storeId, payload) => seller(`/stores/${storeId}/payment-settings`, { method: 'PUT', body: payload }),
    createStore: (payload) => seller('/stores/', { method: 'POST', body: payload }),
    updateStore: (id, payload) => seller(`/stores/${id}`, { method: 'PUT', body: payload }),
    uploadStoreLogo: (id, file) => {
      const body = new FormData()
      body.append('logo', file)
      return seller(`/stores/${id}/logo`, { method: 'POST', body })
    },
    deleteStore: (id) => seller(`/stores/${id}`, { method: 'DELETE' }),
    adminRequests: (storeId) => seller(`/stores/${storeId}/admin-requests`),
    decideAdminRequest: (storeId, membershipId, status) =>
      seller(`/stores/${storeId}/admin-requests/${membershipId}`, { method: 'PATCH', body: { status } }),
    members: (storeId) => seller(`/stores/${storeId}/members`),
    addMember: (storeId, payload) => seller(`/stores/${storeId}/members`, { method: 'POST', body: payload }),
    updateMember: (storeId, membershipId, payload) => seller(`/stores/${storeId}/members/${membershipId}`, { method: 'PATCH', body: payload }),

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
