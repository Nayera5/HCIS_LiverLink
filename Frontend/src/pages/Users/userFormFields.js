import { JOB_TITLE_LABELS, JOB_TITLE_OPTIONS } from '../../auth/roles.js'
import { validateUsername } from '../../utils/validation.js'

export const JOB_TITLE_SELECT_OPTIONS = JOB_TITLE_OPTIONS.map(({ group, options }) => ({
  group,
  options: options.map((value) => ({ value, label: JOB_TITLE_LABELS[value] })),
}))

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Client-side checks for the staff account form; the backend validates everything again. */
export function validateStaffForm(values, { creating }) {
  const errors = {}
  if (creating) {
    const usernameError = validateUsername(values.username)
    if (usernameError) errors.username = usernameError
    if (!values.password) errors.password = 'Set an initial password.'
    else if (values.password.length < 8) errors.password = 'Use at least 8 characters.'
    if (values.password && values.confirmPassword !== values.password) {
      errors.confirmPassword = 'The passwords do not match.'
    }
  }
  if (!values.first_name.trim()) errors.first_name = 'Enter a first name.'
  if (!values.last_name.trim()) errors.last_name = 'Enter a last name.'
  if (values.email.trim() && !EMAIL_PATTERN.test(values.email.trim())) {
    errors.email = 'Enter a valid email address.'
  }
  if (!values.job_title) errors.job_title = 'Choose a job title.'
  return errors
}
