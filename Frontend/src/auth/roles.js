// Display labels for roles and job titles (values match the backend).

export const ROLE_LABELS = {
  admin: 'Admin',
  clinical_staff: 'Clinical staff',
  patient: 'Patient',
}

export const JOB_TITLE_LABELS = {
  hepatologist: 'Hepatologist',
  radiologist: 'Radiologist',
  transplant_surgeon: 'Transplant surgeon',
  transplant_coordinator: 'Transplant coordinator',
  super_admin: 'Super admin',
  billing_admin: 'Billing admin',
}

export const JOB_TITLE_OPTIONS = [
  { group: 'Clinical staff', options: ['hepatologist', 'radiologist', 'transplant_surgeon', 'transplant_coordinator'] },
  { group: 'Administration', options: ['super_admin', 'billing_admin'] },
]

const DOCTOR_TITLES = new Set(['hepatologist', 'radiologist', 'transplant_surgeon'])

/** "Dr. Mona" for doctors, otherwise the first name (or username). */
export function greetingName(user) {
  if (!user) return ''
  const first = user.first_name || user.username
  return DOCTOR_TITLES.has(user.job_title) ? `Dr. ${first}` : first
}

export function displayName(user) {
  if (!user) return ''
  return user.full_name || [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username
}

/** Job title for staff, otherwise the role label. */
export function roleLine(user) {
  if (!user) return ''
  if (user.job_title) return JOB_TITLE_LABELS[user.job_title] || user.job_title
  if (user.role === 'patient') return 'Patient portal'
  return `${ROLE_LABELS[user.role] || user.role} · no job title`
}

export function initials(user) {
  const name = displayName(user)
  const parts = name.split(/[\s._-]+/).filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '?'
}
