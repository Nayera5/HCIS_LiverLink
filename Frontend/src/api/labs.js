// Laboratory API (backend: apps/labs). Permissions are enforced server-side.
import { authRequest, toQuery } from './http'

/** The test catalog (plain array, not paginated). */
export function listLabTests() {
  return authRequest('/lab/tests/')
}

/** params: { patient, encounter, status, priority, page, page_size } */
export function listLabOrders(params = {}) {
  return authRequest(`/lab/orders/${toQuery(params)}`)
}

/** data: { patient, encounter, priority, tests: [labTestId, ...] } */
export function createLabOrder(data) {
  return authRequest('/lab/orders/', { method: 'POST', body: data })
}

export function getLabOrder(id) {
  return authRequest(`/lab/orders/${id}/`)
}

export function cancelLabOrder(id) {
  return authRequest(`/lab/orders/${id}/cancel/`, { method: 'POST' })
}

/** Shows the resulted tests of the order to the patient portal. */
export function releaseLabOrder(id) {
  return authRequest(`/lab/orders/${id}/release/`, { method: 'POST' })
}

/** Tests still waiting for the external lab. params: { patient, priority, page, page_size } */
export function listPendingTests(params = {}) {
  return authRequest(`/lab/pending/${toQuery(params)}`)
}

/** Enter (or correct) a result received from the external lab. */
export function enterLabResult(resultId, value) {
  return authRequest(`/lab/results/${resultId}/enter/`, { method: 'POST', body: { value } })
}

/** params: { test (code), page, page_size } */
export function listPatientResults(patientId, params = {}) {
  return authRequest(`/lab/patients/${patientId}/results/${toQuery(params)}`)
}

export function getPatientTrend(patientId, testCode) {
  return authRequest(`/lab/patients/${patientId}/trends/${toQuery({ test: testCode })}`)
}

/** The signed-in patient's own orders, with a status per test (no values). params: { encounter, page, page_size } */
export function listMyLabOrders(params = {}) {
  return authRequest(`/lab/my/orders/${toQuery(params)}`)
}

/** The signed-in patient's RELEASED results. */
export function listMyResults(params = {}) {
  return authRequest(`/lab/my/results/${toQuery(params)}`)
}

export function getMyTrend(testCode) {
  return authRequest(`/lab/my/trends/${toQuery({ test: testCode })}`)
}
