// Patient registry API (backend: apps/registry). Permissions are enforced server-side.
import { apiRequest } from './client'
import { authRequest, toQuery } from './http'

/** params: { search, category, sex, ordering, page, page_size } */
export function listPatients(params = {}) {
  return authRequest(`/patients/${toQuery(params)}`)
}

/** Counts by category (no patient data). */
export function getPatientSummary() {
  return authRequest('/patients/summary/')
}

export function getPatient(id) {
  return authRequest(`/patients/${id}/`)
}

/** Staff registration: creates a hospital record without a login account. */
export function registerPatient(data) {
  return authRequest('/patients/', { method: 'POST', body: data })
}

export function updatePatient(id, changes) {
  return authRequest(`/patients/${id}/`, { method: 'PATCH', body: changes })
}

export function changePatientCategory(id, category) {
  return authRequest(`/patients/${id}/category/`, { method: 'POST', body: { category } })
}

/** Dashboard data: counts by category + the 5 newest records (list reads are not audited). */
export async function loadPatientOverview() {
  const [summary, recent] = await Promise.all([
    getPatientSummary(),
    listPatients({ ordering: '-created_at', page_size: 5 }),
  ])
  return { summary, recent: recent.results }
}

/** Dashboard card: own MRN, category and phone only. Not audited (a dashboard visit is not a record view). */
export function getMyRecordSummary() {
  return authRequest('/patients/me/summary/')
}

/** The signed-in patient's own record (My Health Record page). Audited as a profile view. */
export function getMyRecord() {
  return authRequest('/patients/me/')
}

/** Patients may change only phone, address and emergency_contact. */
export function updateMyContactDetails(changes) {
  return authRequest('/patients/me/', { method: 'PATCH', body: changes })
}

/** Public portal sign-up: account + own patient record. */
export function selfRegister(data) {
  return apiRequest('/patients/register/', { method: 'POST', body: data })
}
