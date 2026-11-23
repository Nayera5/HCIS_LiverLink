// Transplant & follow-up API (backend: apps/transplant). Permissions enforced server-side.
import { authRequest, toQuery } from './http'

// ── Transplant Cases ────────────────────────────────────────────────────
/** params: { search, status, page, page_size } */
export function listCases(params = {}) {
  return authRequest(`/transplant/cases/${toQuery(params)}`)
}

export function getCase(id) {
  return authRequest(`/transplant/cases/${id}/`)
}

export function createReferral(data) {
  return authRequest('/transplant/cases/', { method: 'POST', body: data })
}

export function updateCaseStatus(id, status) {
  return authRequest(`/transplant/cases/${id}/status/`, { method: 'POST', body: { status } })
}

export function updateCase(id, data) {
  return authRequest(`/transplant/cases/${id}/update/`, { method: 'PATCH', body: data })
}

// ── Case Donors ─────────────────────────────────────────────────────────
export function listCaseDonors(caseId) {
  return authRequest(`/transplant/cases/${caseId}/donors/`)
}

export function addCaseDonor(caseId, data) {
  return authRequest(`/transplant/cases/${caseId}/donors/`, { method: 'POST', body: data })
}

export function getCaseDonor(id) {
  return authRequest(`/transplant/donors/${id}/`)
}

export function updateDonorStatus(id, status) {
  return authRequest(`/transplant/donors/${id}/status/`, { method: 'POST', body: { status } })
}

export function checkABO(donorId) {
  return authRequest(`/transplant/donors/${donorId}/abo-check/`)
}

// ── Checklist ───────────────────────────────────────────────────────────
export function listChecklist(caseId) {
  return authRequest(`/transplant/cases/${caseId}/checklist/`)
}

export function createChecklistItem(caseId, data) {
  return authRequest(`/transplant/cases/${caseId}/checklist/`, { method: 'POST', body: data })
}

export function updateChecklistItem(id, data) {
  return authRequest(`/transplant/checklist/${id}/`, { method: 'PATCH', body: data })
}

export function updateChecklistStatus(id, status) {
  return authRequest(`/transplant/checklist/${id}/status/`, { method: 'POST', body: { status } })
}

export function deleteChecklistItem(id) {
  return authRequest(`/transplant/checklist/${id}/`, { method: 'DELETE' })
}

// ── Committee Decisions ─────────────────────────────────────────────────
export function listDecisions(caseId) {
  return authRequest(`/transplant/cases/${caseId}/decisions/`)
}

export function createDecision(caseId, data) {
  return authRequest(`/transplant/cases/${caseId}/decisions/`, { method: 'POST', body: data })
}

export function getDecision(id) {
  return authRequest(`/transplant/decisions/${id}/`)
}

// ── Surgery ─────────────────────────────────────────────────────────────
export function listSurgeries(caseId) {
  return authRequest(`/transplant/cases/${caseId}/surgeries/`)
}

export function createSurgery(caseId, data) {
  return authRequest(`/transplant/cases/${caseId}/surgeries/`, { method: 'POST', body: data })
}

export function getSurgery(id) {
  return authRequest(`/transplant/surgeries/${id}/`)
}

export function updateSurgery(id, data) {
  return authRequest(`/transplant/surgeries/${id}/`, { method: 'PATCH', body: data })
}

export function completeSurgery(id, data = {}) {
  return authRequest(`/transplant/surgeries/${id}/complete/`, { method: 'POST', body: data })
}

export function listSurgeryTeam(surgeryId) {
  return authRequest(`/transplant/surgeries/${surgeryId}/team/`)
}

export function addTeamMember(surgeryId, data) {
  return authRequest(`/transplant/surgeries/${surgeryId}/team/`, { method: 'POST', body: data })
}

export function removeTeamMember(id) {
  return authRequest(`/transplant/team-members/${id}/`, { method: 'DELETE' })
}

// ── Follow-up ───────────────────────────────────────────────────────────
/** params: { case, patient_role, status } */
export function listFollowUpPlans(params = {}) {
  return authRequest(`/transplant/followup/plans/${toQuery(params)}`)
}

export function getFollowUpPlan(id) {
  return authRequest(`/transplant/followup/plans/${id}/`)
}

export function updateFollowUpPlan(id, data) {
  return authRequest(`/transplant/followup/plans/${id}/`, { method: 'PATCH', body: data })
}

export function listFollowUpVisits(planId, params = {}) {
  return authRequest(`/transplant/followup/plans/${planId}/visits/${toQuery(params)}`)
}

export function createFollowUpVisit(planId, data) {
  return authRequest(`/transplant/followup/plans/${planId}/visits/`, { method: 'POST', body: data })
}

export function getFollowUpVisit(id) {
  return authRequest(`/transplant/followup/visits/${id}/`)
}

export function updateFollowUpVisit(id, data) {
  return authRequest(`/transplant/followup/visits/${id}/`, { method: 'PATCH', body: data })
}

export function getRecoveryStats(planId) {
  return authRequest(`/transplant/followup/plans/${planId}/recovery/`)
}
