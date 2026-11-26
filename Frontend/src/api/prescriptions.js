// Prescriptions & treatment plans API (backend: apps/prescriptions). Permissions are enforced server-side.
import { authRequest, toQuery } from './http'

// ------------------------------------------------------------------ drug catalog

/** Autocomplete search (plain array). params: { q, include_inactive } */
export function searchDrugs(params = {}) {
  return authRequest(`/rx/drugs/${toQuery(params)}`)
}

/** data: { name, generic_name, drug_class, default_route, common_dose } (drugs.manage) */
export function createDrug(data) {
  return authRequest('/rx/drugs/', { method: 'POST', body: data })
}

export function updateDrug(id, changes) {
  return authRequest(`/rx/drugs/${id}/`, { method: 'PATCH', body: changes })
}

// ------------------------------------------------------------------ prescriptions

/** params: { patient, encounter, status, page, page_size } */
export function listPrescriptions(params = {}) {
  return authRequest(`/rx/prescriptions/${toQuery(params)}`)
}

/** data: { patient, encounter, drug, dose, route, frequency, start_date, end_date?, instructions? } */
export function createPrescription(data) {
  return authRequest('/rx/prescriptions/', { method: 'POST', body: data })
}

export function stopPrescription(id, reason) {
  return authRequest(`/rx/prescriptions/${id}/stop/`, { method: 'POST', body: { reason } })
}

export function completePrescription(id, reason = '') {
  return authRequest(`/rx/prescriptions/${id}/complete/`, { method: 'POST', body: { reason } })
}

/** { current: [...], past: [...] } */
export function getPatientMedications(patientId) {
  return authRequest(`/rx/patients/${patientId}/medications/`)
}

/** params: { encounter } */
export function getMyMedications(params = {}) {
  return authRequest(`/rx/my/medications/${toQuery(params)}`)
}

// ------------------------------------------------------------------ treatment plans

/** params: { patient, status, plan_type, review_due: 1, page, page_size } */
export function listTreatmentPlans(params = {}) {
  return authRequest(`/rx/plans/${toQuery(params)}`)
}

/** data: { patient, encounter, plan_type, goals, steps?, start_date, review_date? } */
export function createTreatmentPlan(data) {
  return authRequest('/rx/plans/', { method: 'POST', body: data })
}

/** changes: any of { plan_type, goals, steps, start_date, review_date } plus a mandatory `reason`. */
export function updateTreatmentPlan(id, changes) {
  return authRequest(`/rx/plans/${id}/`, { method: 'PATCH', body: changes })
}

export function completeTreatmentPlan(id, reason) {
  return authRequest(`/rx/plans/${id}/complete/`, { method: 'POST', body: { reason } })
}

export function cancelTreatmentPlan(id, reason) {
  return authRequest(`/rx/plans/${id}/cancel/`, { method: 'POST', body: { reason } })
}

/** Plain array of the signed-in patient's plans. */
export function getMyTreatmentPlans() {
  return authRequest('/rx/my/plans/')
}
