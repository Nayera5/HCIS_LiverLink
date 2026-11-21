// Donor applications API (backend: apps/registry/donor_views.py). Permissions are enforced server-side.
import { authRequest, toQuery } from './http'

// ---- donor portal (self.donor_applications)

/** { can_apply, reason, results: [own applications] } */
export function getMyApplications() {
  return authRequest('/donor-applications/mine/')
}

/** data: { recipient_mrn, relationship } */
export function submitMyApplication(data) {
  return authRequest('/donor-applications/mine/', { method: 'POST', body: data })
}

export function withdrawMyApplication(id) {
  return authRequest(`/donor-applications/mine/${id}/withdraw/`, { method: 'POST' })
}

// ---- staff (donor_applications.view / .screen / .submit_on_behalf)

/** params: { status, search, donor, recipient, page, page_size } */
export function listApplications(params = {}) {
  return authRequest(`/donor-applications/${toQuery(params)}`)
}

export function getApplication(id) {
  return authRequest(`/donor-applications/${id}/`)
}

/** Coordinator on the donor's behalf. data: { donor_mrn, recipient_mrn, relationship } */
export function submitApplicationForDonor(data) {
  return authRequest('/donor-applications/', { method: 'POST', body: data })
}

/** data: { status: 'screening'|'accepted'|'rejected', screening_notes? } */
export function setApplicationStatus(id, data) {
  return authRequest(`/donor-applications/${id}/status/`, { method: 'POST', body: data })
}

export function withdrawApplication(id) {
  return authRequest(`/donor-applications/${id}/withdraw/`, { method: 'POST' })
}
