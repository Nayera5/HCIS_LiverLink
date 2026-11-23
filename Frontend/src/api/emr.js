// EMR API (backend: apps/emr/views.py, mounted at /api/emr/). Permissions are enforced server-side:
// emr.view reads every patient, emr.write (doctors) changes records, portal users get their own
// released records only (the backend filters the lists, so no patient id is needed).
import { authRequest, toQuery } from './http'

// --- Encounters ------------------------------------------------------------
export function listEncounters(params = {}) {
  return authRequest(`/emr/encounters/${toQuery(params)}`)
}

/** One encounter with its diagnoses, vital signs and addenda. */
export function getEncounter(id) {
  return authRequest(`/emr/encounters/${id}/`)
}

/** data: { patient, chief_complaint, clinical_notes }. The treating doctor is the signed-in doctor. */
export function createEncounter(data) {
  return authRequest('/emr/encounters/', { method: 'POST', body: data })
}

export function updateEncounter(id, changes) {
  return authRequest(`/emr/encounters/${id}/`, { method: 'PATCH', body: changes })
}

export function deleteEncounter(id) {
  return authRequest(`/emr/encounters/${id}/`, { method: 'DELETE' })
}

/** Final: a signed encounter can only be amended with addenda. Treating doctor only. */
export function signEncounter(id) {
  return authRequest(`/emr/encounters/${id}/sign/`, { method: 'POST' })
}

export function addAddendum(encounterId, text) {
  return authRequest(`/emr/encounters/${encounterId}/addenda/`, { method: 'POST', body: { text } })
}

// --- Diagnoses and vital signs (belong to an encounter) ----------------------
/** data: { encounter, icd10_code, description, is_primary, status } */
export function createDiagnosis(data) {
  return authRequest('/emr/diagnoses/', { method: 'POST', body: data })
}

export function updateDiagnosis(id, changes) {
  return authRequest(`/emr/diagnoses/${id}/`, { method: 'PATCH', body: changes })
}

export function deleteDiagnosis(id) {
  return authRequest(`/emr/diagnoses/${id}/`, { method: 'DELETE' })
}

/** data: { encounter, bp_systolic, bp_diastolic, pulse, temperature, weight_kg, height_cm }. BMI is computed. */
export function createVitals(data) {
  return authRequest('/emr/vital-signs/', { method: 'POST', body: data })
}

export function deleteVitals(id) {
  return authRequest(`/emr/vital-signs/${id}/`, { method: 'DELETE' })
}

// --- Medical history ----------------------------------------------------------
export function listHistory(params = {}) {
  return authRequest(`/emr/medical-history/${toQuery(params)}`)
}

/** data: { patient, history_type, description, onset_date } */
export function createHistory(data) {
  return authRequest('/emr/medical-history/', { method: 'POST', body: data })
}

export function deleteHistory(id) {
  return authRequest(`/emr/medical-history/${id}/`, { method: 'DELETE' })
}

// --- Documents ----------------------------------------------------------------
export function listDocuments(params = {}) {
  return authRequest(`/emr/documents/${toQuery(params)}`)
}

/** formData: patient, title, document_type, file_path (File). PDF, JPG or PNG up to 20 MB. */
export function uploadDocument(formData) {
  return authRequest('/emr/documents/', { method: 'POST', body: formData })
}

/** Show (true) or hide (false) the document in the patient portal. */
export function releaseDocument(id, isReleased = true) {
  return authRequest(`/emr/documents/${id}/release/`, { method: 'POST', body: { is_released: isReleased } })
}

export function deleteDocument(id) {
  return authRequest(`/emr/documents/${id}/`, { method: 'DELETE' })
}

/** The file as a Blob (the download needs the access token, so a plain link would not work). */
export function downloadDocument(id) {
  return authRequest(`/emr/documents/${id}/download/`, { responseType: 'blob' })
}
