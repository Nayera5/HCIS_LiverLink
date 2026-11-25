// Imaging orders and scan bookings API (backend: apps/radiology). Permissions are enforced server-side.
import { authRequest, toQuery } from './http'

const post = (path, body = {}) => authRequest(`/radiology/${path}`, { method: 'POST', body })

// --- Orders (staff) ---------------------------------------------------------------------
/** params: { patient, encounter, status, billing_service, booking ('none' | 'pending'), page, page_size } */
export function listImagingOrders(params = {}) {
  return authRequest(`/radiology/orders/${toQuery(params)}`)
}

export function getImagingOrder(id) {
  return authRequest(`/radiology/orders/${id}/`)
}

/** data: { patient, billing_service (active imaging service id), clinical_indication, encounter? } */
export const createImagingOrder = (data) => post('orders/', data)

/** data: { status: 'scheduled' (confirm the booking) | 'acquired' | 'cancelled', reason? (required to cancel) } */
export const changeImagingOrderStatus = (id, data) => post(`orders/${id}/status/`, data)

/** Free scan slots for an order: [{ slot_id, start_time, end_time }]. params: { date } */
export function listOrderSlots(id, params = {}) {
  return authRequest(`/radiology/orders/${id}/slots/${toQuery(params)}`)
}

/** Book, or move the booking (radiologist: confirmed at once). */
export const bookScan = (id, slot) => post(`orders/${id}/booking/`, { slot })
export const cancelScanBooking = (id, reason) => post(`orders/${id}/booking/cancel/`, { reason })
export const markScanNoShow = (id) => post(`orders/${id}/booking/no-show/`)

/** Coordinator: remind the patient. */
export const remindPatient = (id) => post(`orders/${id}/remind/`)

// --- Own orders (patient portal) -----------------------------------------------------------
export function listMyImagingOrders() {
  return authRequest('/radiology/my-orders/')
}

export function listMyOrderSlots(id, params = {}) {
  return authRequest(`/radiology/my-orders/${id}/slots/${toQuery(params)}`)
}

export const bookMyScan = (id, slot) => post(`my-orders/${id}/booking/`, { slot })
export const cancelMyScan = (id) => post(`my-orders/${id}/booking/cancel/`)

// --- Scan slots (radiologist) ---------------------------------------------------------------
/** params: { billing_service, date_from, date_to, page, page_size } */
export function listScanSlots(params = {}) {
  return authRequest(`/radiology/slots/${toQuery(params)}`)
}

/** data: { billing_service, resource_name?, date, start_time, end_time, slot_minutes, is_published } */
export const createScanSlots = (data) => post('slots/', data)

export function publishScanSlot(id, isPublished) {
  return authRequest(`/radiology/slots/${id}/`, { method: 'PATCH', body: { is_published: isPublished } })
}

export function deleteScanSlot(id) {
  return authRequest(`/radiology/slots/${id}/`, { method: 'DELETE' })
}
