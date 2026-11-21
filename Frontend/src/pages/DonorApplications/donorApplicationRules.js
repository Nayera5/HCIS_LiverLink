// Donor applications: labels, form checks and screening rules (no React, so `npm test` can import it).
// Mirrors apps/registry (DonorApplication.SCREENING_TRANSITIONS and donor_serializers.py).
// The backend is the authority; these checks only give earlier, friendlier feedback.

export const STATUS_LABELS = {
  submitted: 'Submitted',
  screening: 'Screening',
  accepted: 'Accepted',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
}

export const STATUS_TONES = {
  submitted: 'info',
  screening: 'warning',
  accepted: 'success',
  rejected: 'danger',
  withdrawn: 'neutral',
}

// Open = can still be withdrawn. `accepted` is approval for the next evaluation stage, not medical
// clearance, so it stays open; only rejected and withdrawn are terminal.
export const OPEN_STATUSES = new Set(['submitted', 'screening', 'accepted'])
export const TERMINAL_STATUSES = new Set(['rejected', 'withdrawn'])

export const STATUS_FILTER_OPTIONS = [
  { value: 'open', label: 'Open (not rejected or withdrawn)' },
  ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label })),
]

/** Button wording for each screening decision. */
export const DECISION_LABELS = {
  screening: 'Start screening',
  accepted: 'Accept',
  rejected: 'Reject',
}

const MRN_PATTERN = /^LL-\d{6,}$/

/** "ll-000123 " → "LL-000123" (the backend accepts the same forms). */
export function normalizeMrn(value) {
  return (value || '').trim().toUpperCase()
}

function checkMrn(value, missing) {
  const mrn = normalizeMrn(value)
  if (!mrn) return missing
  if (!MRN_PATTERN.test(mrn)) return 'Enter an MRN like LL-000123.'
  return ''
}

/**
 * Field errors for a new application. `donorMrn` is checked only for staff submissions
 * ({ forDonor: true }); a donor's own MRN is never typed by the donor.
 */
export function validateApplication(values, { forDonor = false, ownMrn = '' } = {}) {
  const errors = {}
  const recipient = checkMrn(values.recipient_mrn, "Enter the recipient's MRN.")
  if (recipient) errors.recipient_mrn = recipient
  if (forDonor) {
    const donor = checkMrn(values.donor_mrn, "Enter the donor's MRN.")
    if (donor) errors.donor_mrn = donor
  }
  const donorMrn = forDonor ? normalizeMrn(values.donor_mrn) : normalizeMrn(ownMrn)
  if (!errors.recipient_mrn && donorMrn && normalizeMrn(values.recipient_mrn) === donorMrn) {
    errors.recipient_mrn = 'The donor and the recipient must be different people.'
  }
  if (!(values.relationship || '').trim()) {
    errors.relationship = 'Describe the relationship to the recipient (e.g. son, wife).'
  } else if (values.relationship.trim().length > 50) {
    errors.relationship = 'Keep the relationship under 50 characters.'
  }
  return errors
}

/** Request body for a new application (trimmed; MRNs normalised). */
export function applicationPayload(values, { forDonor = false } = {}) {
  const body = { recipient_mrn: normalizeMrn(values.recipient_mrn), relationship: values.relationship.trim() }
  if (forDonor) body.donor_mrn = normalizeMrn(values.donor_mrn)
  return body
}

/** A rejection needs a reason (typed now or already saved on the application). */
export function validateDecision(status, notes, existingNotes = '') {
  if (status === 'rejected' && !(notes || '').trim() && !(existingNotes || '').trim()) {
    return { screening_notes: 'Give the reason for rejecting the application.' }
  }
  return {}
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

export function isOpen(status) {
  return OPEN_STATUSES.has(status)
}

export function isTerminal(status) {
  return TERMINAL_STATUSES.has(status)
}
