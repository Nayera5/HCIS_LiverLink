// Billing & Payments API (backend: apps/billing). Permissions are enforced server-side.
import { authRequest, downloadFile, toQuery } from './http'

// --------------------------------------------------------------------------- service catalog

/** params: { category, active_only } */
export function listServices(params = {}) {
  return authRequest(`/services/${toQuery(params)}`)
}

export function createService(data) {
  return authRequest('/services/', { method: 'POST', body: data })
}

export function updateService(id, changes) {
  return authRequest(`/services/${id}/`, { method: 'PATCH', body: changes })
}

// --------------------------------------------------------------------------- invoices (staff)

/** params: { patient, status, page, page_size } */
export function listInvoices(params = {}) {
  return authRequest(`/invoices/${toQuery(params)}`)
}

export function getInvoice(id) {
  return authRequest(`/invoices/${id}/`)
}

/** { patient, due_date, items: [{ service, quantity }] } */
export function createInvoice(data) {
  return authRequest('/invoices/', { method: 'POST', body: data })
}

export function cancelInvoice(id) {
  return authRequest(`/invoices/${id}/cancel/`, { method: 'POST' })
}

/** { amount, method: 'cash' | 'card' } */
export function recordPayment(invoiceId, data) {
  return authRequest(`/invoices/${invoiceId}/payments/`, { method: 'POST', body: data })
}

/** One patient's outstanding balance and invoice history. */
export function getPatientInvoices(patientId) {
  return authRequest(`/patients/${patientId}/invoices/`)
}

// --------------------------------------------------------------------------- patient portal

export function getMyInvoices() {
  return authRequest('/invoices/me/')
}

export function getMyInvoice(id) {
  return authRequest(`/invoices/me/${id}/`)
}

// --------------------------------------------------------------------------- receipts (PDF)

export function downloadReceipt(paymentId) {
  return downloadFile(`/payments/${paymentId}/receipt/`, `receipt-${paymentId}.pdf`)
}

export function downloadMyReceipt(paymentId) {
  return downloadFile(`/payments/me/${paymentId}/receipt/`, `receipt-${paymentId}.pdf`)
}
