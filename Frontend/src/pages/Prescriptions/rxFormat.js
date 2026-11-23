// Pure helpers for prescriptions & treatment plans (unit-tested in rxFormat.test.js).

export const ROUTE_LABELS = {
  oral: 'Oral',
  iv: 'Intravenous (IV)',
  im: 'Intramuscular (IM)',
  sc: 'Subcutaneous (SC)',
  topical: 'Topical',
}
export const ROUTE_OPTIONS = Object.entries(ROUTE_LABELS).map(([value, label]) => ({ value, label }))

export const PLAN_TYPE_LABELS = {
  surveillance: 'Surveillance',
  antiviral: 'Antiviral therapy',
  ablation: 'Ablation',
  tace: 'Chemoembolization (TACE)',
  resection: 'Resection',
  transplant_referral: 'Transplant referral',
  supportive: 'Supportive care',
}
export const PLAN_TYPE_OPTIONS = Object.entries(PLAN_TYPE_LABELS).map(([value, label]) => ({ value, label }))

export const FREQUENCY_SUGGESTIONS = [
  'once daily', 'twice daily', 'three times daily', 'four times daily', 'every 8 hours', 'every 12 hours',
  'at bedtime', 'once weekly', 'every 3 weeks', 'as needed',
]

/** Today's date as YYYY-MM-DD in the browser's local time zone. */
export function todayIso(now = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

/** "2026-01-30" + 3 days -> "2026-02-02" (calendar arithmetic, no time-zone drift). */
export function addDays(isoDate, days) {
  const [y, m, d] = isoDate.split('-').map(Number)
  const date = new Date(Date.UTC(y, m - 1, d + Number(days)))
  return date.toISOString().slice(0, 10)
}

/** Whole days from start to end (both YYYY-MM-DD). */
export function daysBetween(startIso, endIso) {
  return Math.round((Date.parse(`${endIso}T00:00:00Z`) - Date.parse(`${startIso}T00:00:00Z`)) / 86400000)
}

/**
 * Client-side mirror of the backend rules for a new prescription. Returns { field: message }.
 * durationDays (optional) is converted to an end date by the form, so only end_date is checked here.
 */
export function validatePrescription(form) {
  const errors = {}
  if (!form.drug) errors.drug = 'Choose a drug from the catalog.'
  if (!form.dose?.trim()) errors.dose = 'Enter the dose per intake, e.g. 300 mg.'
  if (!form.route) errors.route = 'Choose a route.'
  if (!form.frequency?.trim()) errors.frequency = 'Enter how often, e.g. twice daily.'
  if (!form.start_date) errors.start_date = 'Enter the first day.'
  if (form.duration_days !== '' && form.duration_days != null) {
    const n = Number(form.duration_days)
    if (!Number.isInteger(n) || n < 1) errors.duration_days = 'Duration must be a whole number of days (1 or more).'
  }
  if (form.start_date && form.end_date && form.end_date <= form.start_date) {
    errors.end_date = 'The end date must be after the start date.'
  }
  return errors
}

export function validatePlan(form, { editing = false } = {}) {
  const errors = {}
  if (!form.plan_type) errors.plan_type = 'Choose the kind of treatment.'
  if (!form.goals?.trim()) errors.goals = 'Describe what the plan aims to achieve.'
  if (!form.start_date) errors.start_date = 'Enter the first day.'
  if (form.start_date && form.review_date && form.review_date < form.start_date) {
    errors.review_date = 'The review date cannot be before the start date.'
  }
  if (editing && !form.reason?.trim()) errors.reason = 'Give a reason for this change (it is kept in the audit log).'
  return errors
}

/** Only the fields that differ from the stored plan (what PATCH needs). */
export function changedPlanFields(original, form) {
  const out = {}
  for (const key of ['plan_type', 'goals', 'steps', 'start_date', 'review_date']) {
    const before = original[key] ?? ''
    const after = form[key] ?? ''
    if (before !== after) out[key] = key === 'review_date' && after === '' ? null : after
  }
  return out
}

/** Review state of an active plan: 'overdue' (passed), 'soon' (within 14 days), or ''. */
export function reviewState(plan, today = todayIso()) {
  if (plan.status !== 'active' || !plan.review_date) return ''
  if (plan.review_date < today) return 'overdue'
  if (plan.review_date === today) return 'today'
  return daysBetween(today, plan.review_date) <= 14 ? 'soon' : ''
}

/** "300 mg · Oral · twice daily" */
export function regimenText(rx) {
  return [rx.dose, ROUTE_LABELS[rx.route] || rx.route, rx.frequency].filter(Boolean).join(' · ')
}
