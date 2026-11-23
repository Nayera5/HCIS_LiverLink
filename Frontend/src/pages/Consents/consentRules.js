// Consents: labels, eligibility and form checks (no React, so `npm test` can import it).
// Mirrors apps/registry (models.Consent and consent_serializers.py); the backend is the authority.
// Stage 6 covers surgery consents only; ct_contrast and data_use (spec §4.7) are deferred.

export const CONSENT_TYPE_LABELS = {
  donor_surgery: 'Donor surgery',
  transplant_surgery: 'Transplant surgery',
}

export const STATUS_LABELS = { signed: 'Signed', withdrawn: 'Withdrawn' }
export const STATUS_TONES = { signed: 'success', withdrawn: 'neutral' }

// Which consent type can be recorded for a patient's current category.
const ELIGIBLE = {
  donor_surgery: ['donor'],
  transplant_surgery: ['recipient'],
}

/** Consent types that may be recorded for this category (and that are not already active). */
export function availableTypes(category, consents = []) {
  const active = new Set(consents.filter((c) => c.status === 'signed').map((c) => c.consent_type))
  return Object.keys(CONSENT_TYPE_LABELS).filter((type) => ELIGIBLE[type].includes(category) && !active.has(type))
}

/** Why no consent can be recorded right now (empty string when one can). */
export function unavailableReason(category, consents = []) {
  if (availableTypes(category, consents).length) return ''
  const eligible = Object.keys(ELIGIBLE).filter((type) => ELIGIBLE[type].includes(category))
  if (!eligible.length) {
    return 'Surgery consents can be recorded for living donors (donor surgery) and transplant recipients (transplant surgery).'
  }
  return 'This person already has an active consent of each type that applies. Withdraw it before recording a new one.'
}

/** "2026-03-01T09:30" (datetime-local, browser time) → ISO string for the API; '' when invalid. */
export function toIsoDateTime(local) {
  if (!local) return ''
  const date = new Date(local)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

/** Date → value for <input type="datetime-local"> in browser time. */
export function toLocalInput(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/**
 * Field errors for recording a consent.
 * values: { consent_type, signed_at (datetime-local string), witnessed_by }
 * context: { category, dateOfBirth ('YYYY-MM-DD'), consents (current list), now (Date) }
 */
export function validateConsent(values, { category, dateOfBirth, consents = [], now = new Date() } = {}) {
  const errors = {}
  if (!values.consent_type) {
    errors.consent_type = 'Choose the consent type.'
  } else if (!availableTypes(category, consents).includes(values.consent_type)) {
    errors.consent_type = 'This consent type cannot be recorded for this person right now.'
  }
  const iso = toIsoDateTime(values.signed_at)
  if (!values.signed_at) {
    errors.signed_at = 'Enter when the form was signed.'
  } else if (!iso) {
    errors.signed_at = 'Enter a valid date and time.'
  } else if (new Date(iso) > now) {
    errors.signed_at = 'The signing date cannot be in the future.'
  } else if (dateOfBirth && iso.slice(0, 10) < dateOfBirth) {
    errors.signed_at = 'The signing date is before the date of birth.'
  }
  return errors
}

/** Request body: witness '' (none) becomes null. */
export function consentPayload(values) {
  return {
    consent_type: values.consent_type,
    signed_at: toIsoDateTime(values.signed_at),
    witnessed_by: values.witnessed_by ? Number(values.witnessed_by) : null,
  }
}

export function consentTypeLabel(type) {
  return CONSENT_TYPE_LABELS[type] || type
}
