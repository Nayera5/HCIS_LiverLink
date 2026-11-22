// Consents API (backend: apps/registry/consent_views.py). Permissions are enforced server-side.
import { authRequest } from './http'

/** Full consent history for a patient (consents.view; not Super Admin). */
export function listPatientConsents(patientId) {
  return authRequest(`/patients/${patientId}/consents/`)
}

/** data: { consent_type, signed_at (ISO), witnessed_by: staff id | null } (consents.record) */
export function recordConsent(patientId, data) {
  return authRequest(`/patients/${patientId}/consents/`, { method: 'POST', body: data })
}

export function withdrawConsent(consentId) {
  return authRequest(`/consents/${consentId}/withdraw/`, { method: 'POST' })
}

/** Active staff who can be named as witness (consents.record). */
export function listWitnesses() {
  return authRequest('/consents/witnesses/')
}

/** The signed-in patient's own consents, read-only (self.consents). */
export function getMyConsents() {
  return authRequest('/consents/mine/')
}
