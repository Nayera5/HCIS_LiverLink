import { useState } from 'react'
import { fieldErrors } from '../../api/http'
import { getErrorMessage } from '../../api/auth'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PasswordField from '../../components/ui/PasswordField'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { JOB_TITLE_SELECT_OPTIONS, validateStaffForm } from './userFormFields'

const EMPTY = {
  username: '', password: '', confirmPassword: '', first_name: '', last_name: '', email: '',
  job_title: '', department: '', license_no: '', phone: '',
}

/**
 * Create (`creating`) or edit a staff account. `onSubmit(payload)` returns a promise;
 * field errors from the API are shown next to their fields.
 */
export default function StaffAccountForm({ initial, creating = false, submitLabel, onSubmit, onCancel, lockJobTitle }) {
  const [values, setValues] = useState({ ...EMPTY, ...initial })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => {
    const { name, value } = event.target
    setValues((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const clientErrors = validateStaffForm(values, { creating })
    setErrors(clientErrors)
    setFormError('')
    if (Object.keys(clientErrors).length) {
      event.currentTarget.querySelector(`[name="${Object.keys(clientErrors)[0]}"]`)?.focus()
      return
    }
    const payload = {
      first_name: values.first_name.trim(),
      last_name: values.last_name.trim(),
      email: values.email.trim(),
      job_title: values.job_title,
      department: values.department.trim(),
      license_no: values.license_no.trim(),
      phone: values.phone.trim(),
    }
    if (creating) {
      payload.username = values.username.trim()
      payload.password = values.password
    }
    if (lockJobTitle) delete payload.job_title
    setSaving(true)
    try {
      await onSubmit(payload)
    } catch (error) {
      const fields = fieldErrors(error)
      const { form, ...rest } = fields
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? 'Please correct the highlighted fields.'
        : getErrorMessage(error, 'Could not save the account.')))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      {formError && <Alert variant="error" className="form-alert">{formError}</Alert>}
      <div className="form-grid">
        {creating && (
          <>
            <p className="form-section-title">Sign-in</p>
            <TextField label="Username" name="username" value={values.username} onChange={change}
              error={errors.username} autoComplete="off" autoCapitalize="none" spellCheck={false}
              maxLength={150} hint="Used to sign in. Letters, numbers and @ . + - _ only." required />
            <div className="form-grid__spacer" aria-hidden="true" />
            <PasswordField label="Initial password" name="password" value={values.password} onChange={change}
              error={errors.password} autoComplete="new-password"
              hint="Share it privately; the user can change it after signing in." required />
            <PasswordField label="Confirm password" name="confirmPassword" value={values.confirmPassword}
              onChange={change} error={errors.confirmPassword} autoComplete="new-password" required />
          </>
        )}

        <p className="form-section-title">Person</p>
        <TextField label="First name" name="first_name" value={values.first_name} onChange={change}
          error={errors.first_name} maxLength={150} required />
        <TextField label="Last name" name="last_name" value={values.last_name} onChange={change}
          error={errors.last_name} maxLength={150} required />
        <TextField label={<>Email <span className="field__optional">(optional)</span></>} name="email"
          type="email" value={values.email} onChange={change} error={errors.email} maxLength={254}
          hint="For contact and password recovery." />
        <TextField label={<>Phone <span className="field__optional">(optional)</span></>} name="phone"
          type="tel" value={values.phone} onChange={change} error={errors.phone} maxLength={20} />

        <p className="form-section-title">Role in LiverLink</p>
        <SelectField label="Job title" name="job_title" value={values.job_title} onChange={change}
          error={errors.job_title} placeholder="Choose a job title" options={JOB_TITLE_SELECT_OPTIONS}
          disabled={lockJobTitle}
          hint={lockJobTitle ? 'You cannot change your own job title.'
            : 'Admin titles give the Admin role; clinical titles give Clinical staff.'} required />
        <TextField label={<>Department <span className="field__optional">(optional)</span></>}
          name="department" value={values.department} onChange={change} error={errors.department}
          maxLength={100} />
        <TextField label={<>License number <span className="field__optional">(optional)</span></>}
          name="license_no" value={values.license_no} onChange={change} error={errors.license_no}
          maxLength={50} hint="Medical license or syndicate number. Must be unique." />
      </div>

      <div className="form-actions">
        {onCancel && (
          <Button variant="secondary" onClick={onCancel} disabled={saving}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={saving}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
