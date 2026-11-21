import { useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { BLOOD_GROUP_OPTIONS, CATEGORY_OPTIONS, SEX_OPTIONS } from './patientDisplay'

const EMPTY = {
  first_name: '', last_name: '', date_of_birth: '', sex: '', national_id: '', phone: '', address: '',
  emergency_contact: '', blood_group: '', height_cm: '', weight_kg: '', category: '',
}

const optional = (label) => (
  <>
    {label} <span className="field__optional">(optional)</span>
  </>
)

function todayISO() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

/** Client-side checks for a better experience; the backend validates everything again. */
function validatePatientForm(values, { withCategory }) {
  const errors = {}
  if (!values.first_name.trim()) errors.first_name = 'Enter the first name.'
  if (!values.last_name.trim()) errors.last_name = 'Enter the family name.'
  if (!values.date_of_birth) errors.date_of_birth = 'Enter the date of birth.'
  else if (values.date_of_birth > todayISO()) errors.date_of_birth = 'Date of birth cannot be in the future.'
  if (!values.sex) errors.sex = 'Choose the sex.'
  if (!values.phone.trim()) errors.phone = 'Enter a phone number.'
  if (values.national_id.trim() && !/^\d{14}$/.test(values.national_id.trim())) {
    errors.national_id = 'The national ID must be exactly 14 digits.'
  }
  for (const field of ['height_cm', 'weight_kg']) {
    if (values[field] !== '' && !(Number(values[field]) > 0)) errors[field] = 'Must be greater than 0.'
  }
  if (withCategory && !values.category) errors.category = 'Choose a category.'
  return errors
}

function toPayload(values, { withCategory, initial }) {
  const payload = {
    first_name: values.first_name.trim(),
    last_name: values.last_name.trim(),
    date_of_birth: values.date_of_birth,
    sex: values.sex,
    national_id: values.national_id.trim(),
    phone: values.phone.trim(),
    address: values.address.trim(),
    emergency_contact: values.emergency_contact.trim(),
    blood_group: values.blood_group || null,
    height_cm: values.height_cm === '' ? null : values.height_cm,
    weight_kg: values.weight_kg === '' ? null : values.weight_kg,
  }
  if (withCategory) payload.category = values.category
  if (!initial) return payload
  // Edit: send only what changed.
  return Object.fromEntries(
    Object.entries(payload).filter(([key, value]) => String(value ?? '') !== String(initial[key] ?? '')),
  )
}

/**
 * Patient demographics form for staff registration (`withCategory`) and demographic edits.
 * `onSubmit(payload)` returns a promise; API field errors appear next to their fields.
 */
export default function PatientForm({ initial, withCategory = false, submitLabel, onSubmit, onCancel }) {
  const [values, setValues] = useState(() => {
    const start = { ...EMPTY }
    Object.entries(initial || {}).forEach(([key, value]) => {
      if (key in start) start[key] = value ?? ''
    })
    return start
  })
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
    const clientErrors = validatePatientForm(values, { withCategory })
    setErrors(clientErrors)
    setFormError('')
    if (Object.keys(clientErrors).length) {
      event.currentTarget.querySelector(`[name="${Object.keys(clientErrors)[0]}"]`)?.focus()
      return
    }
    const payload = toPayload(values, { withCategory, initial })
    if (initial && Object.keys(payload).length === 0) {
      setFormError('Nothing has changed.')
      return
    }
    setSaving(true)
    try {
      await onSubmit(payload)
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? 'Please correct the highlighted fields.'
        : getErrorMessage(error, 'Could not save the patient record.')))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      {formError && <Alert variant="error" className="form-alert">{formError}</Alert>}
      <div className="form-grid">
        <p className="form-section-title">Identity</p>
        <TextField label="First name" name="first_name" value={values.first_name} onChange={change}
          error={errors.first_name} maxLength={100} required />
        <TextField label="Family name" name="last_name" value={values.last_name} onChange={change}
          error={errors.last_name} maxLength={100} required />
        <TextField label="Date of birth" name="date_of_birth" type="date" max={todayISO()}
          value={values.date_of_birth} onChange={change} error={errors.date_of_birth} required />
        <SelectField label="Sex" name="sex" value={values.sex} onChange={change} error={errors.sex}
          placeholder="Choose" options={SEX_OPTIONS} required />
        <TextField label={optional('National ID')} name="national_id" inputMode="numeric" maxLength={14}
          value={values.national_id} onChange={change} error={errors.national_id}
          hint="Egyptian national ID, 14 digits. Must be unique." />
        {withCategory && (
          <SelectField label="Category" name="category" value={values.category} onChange={change}
            error={errors.category} placeholder="Choose a category" options={CATEGORY_OPTIONS} required />
        )}

        <p className="form-section-title">Contact</p>
        <TextField label="Phone" name="phone" type="tel" maxLength={20} value={values.phone} onChange={change}
          error={errors.phone} required />
        <TextField label={optional('Emergency contact')} name="emergency_contact" maxLength={200}
          value={values.emergency_contact} onChange={change} error={errors.emergency_contact}
          hint="Name and phone number." />
        <TextField className="form-grid__full" label={optional('Address')} name="address"
          value={values.address} onChange={change} error={errors.address} />

        <p className="form-section-title">Clinical basics</p>
        <SelectField label={optional('Blood group')} name="blood_group" value={values.blood_group}
          onChange={change} error={errors.blood_group} placeholder="Unknown" options={BLOOD_GROUP_OPTIONS} />
        <div className="form-grid__pair">
          <TextField label={optional('Height (cm)')} name="height_cm" type="number" min="0.01" step="0.01"
            value={values.height_cm} onChange={change} error={errors.height_cm} />
          <TextField label={optional('Weight (kg)')} name="weight_kg" type="number" min="0.01" step="0.01"
            value={values.weight_kg} onChange={change} error={errors.weight_kg}
            hint="Needed for GRWR." />
        </div>
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
