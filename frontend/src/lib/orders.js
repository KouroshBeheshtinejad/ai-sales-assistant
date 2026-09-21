// Mirrors SellerOrderService in the backend.
export const STATUS_FLOW = ['pending', 'confirmed', 'preparing', 'shipped', 'delivered']
export const ALL_STATUSES = [...STATUS_FLOW, 'cancelled']
export const TRANSITIONS = {
  pending: ['confirmed', 'cancelled'],
  confirmed: ['preparing', 'cancelled'],
  preparing: ['shipped'],
  shipped: ['delivered'],
  delivered: [],
  cancelled: [],
}
