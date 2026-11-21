import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { selfRegister } from '../../api/patients'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PasswordField from '../../components/ui/PasswordField'
import SelectField from '../../components/ui/SelectField'
import TextField from '../../components/ui/TextField'
import { SIGNUP_PHONE_LENGTH, validateSignupPhone, validateUsername } from '../../utils/validation'
import { SEX_OPTIONS } from '../Patients/patientDisplay'
import AuthLayout from './AuthLayout'
import '../Patients/Patients.css'

const EMPTY = {
  first_name: '', last_name: '', date_of_birth: '', sex: '', national_id: '', phone: '', email: '',
  category: '', username: '', password: '', confirmPassword: '',
}
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function todayISO() {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

function validate(values) {
  const errors = {}
  if (!values.first_name.trim()) errors.first_name = 'Enter your first name.'
  if (!values.last_name.trim()) errors.last_name = 'Enter your family name.'
  if (!values.date_of_birth) errors.date_of_birth = 'Enter your date of birth.'
  else if (values.date_of_birth > todayISO()) errors.date_of_birth = 'Date of birth cannot be in the future.'
  if (!values.sex) errors.sex = 'Choose your sex.'
  if (values.national_id.trim() && !/^\d{14}$/.test(values.national_id.trim())) {
    errors.national_id = 'The national ID must be exactly 14 digits.'
  }
  const phoneError = validateSignupPhone(values.phone)
  if (phoneError) errors.phone = phoneError
  if (!values.email.trim()) errors.email = 'Enter your email address.'
  else if (!EMAIL_PATTERN.test(values.email.trim())) errors.email = 'Enter a valid email address.'
  if (!values.category) errors.category = 'Choose why you are registering.'
  const usernameError = validateUsername(values.username)
  if (usernameError) errors.username = usernameError
  if (!values.password) errors.password = 'Choose a password.'
  else if (values.password.length < 8) errors.password = 'Use at least 8 characters.'
  if (values.password && values.confirmPassword !== values.password) errors.confirmPassword = 'The passwords do not match.'
  return errors
}

/** Public portal sign-up for patients and living donors (creates an account and its own record). */
export default function RegisterPage() {
  const [values, setValues] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(null)

  const change = (event) => {
    const { name, value } = event.target
    setValues((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const submit = async (event) => {
    event.preventDefault()
    const clientErrors = validate(values)
    setErrors(clientErrors)
    setFormError('')
    if (Object.keys(clientErrors).length) {
      event.currentTarget.querySelector(`[name="${Object.keys(clientErrors)[0]}"]`)?.focus()
      return
    }
    setSaving(true)
    try {
      const result = await selfRegister({
        first_name: values.first_name.trim(), last_name: values.last_name.trim(),
        date_of_birth: values.date_of_birth, sex: values.sex, national_id: values.national_id.trim(),
        phone: values.phone.trim(), email: values.email.trim(), category: values.category,
        username: values.username.trim(), password: values.password,
      })
      setDone(result)
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setFormError(form || (Object.keys(rest).length ? 'Please correct the highlighted fields.'
        : getErrorMessage(error, 'Registration is not available right now. Please try again later.')))
      setValues((prev) => ({ ...prev, password: '', confirmPassword: '' }))
    } finally {
      setSaving(false)
    }
  }

  const footer = (
    <p className="login-footnote">
      Already registered? <Link className="login-link" to="/login">Sign in</Link>
    </p>
  )

  if (done) {
    return (
      <AuthLayout title="Registration complete" footer={footer}>
        <div className="login-form">
          <Alert variant="success">{done.detail}</Alert>
          <dl className="detail-list">
            <div><dt>Username</dt><dd>{done.username}</dd></div>
            <div><dt>Medical Record Number</dt><dd>{done.mrn}</dd></div>
          </dl>
          <p className="login-header__subtitle">Keep your MRN: the hospital uses it to find your record.</p>
          <Button as={Link} to="/login" block>Sign in</Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <div className="register-page">
      <AuthLayout
        title="Create your account"
        // subtitle="For liver patients and living donors. Hospital staff accounts are created by the administrator."
        footer={footer}
      >
        <form className="login-form" onSubmit={submit} noValidate>
          {formError && <Alert variant="error">{formError}</Alert>}

          <fieldset className="choice-group">
            <legend>I am registering as</legend>
            <label className="choice">
              <input type="radio" name="category" value="liver_patient" checked={values.category === 'liver_patient'}
                onChange={change} />
              <span><strong>Liver patient</strong>I receive care for a liver condition.</span>
            </label>
            <label className="choice">
              <input type="radio" name="category" value="donor" checked={values.category === 'donor'}
                onChange={change} />
              <span><strong>Living donor</strong>I want to donate part of my liver.</span>
            </label>
          </fieldset>
          {errors.category && <p className="field__error" role="alert">{errors.category}</p>}

          <div className="form-grid">
            <TextField label="First name" name="first_name" value={values.first_name} onChange={change}
              error={errors.first_name} maxLength={100} autoComplete="given-name" />
            <TextField label="Family name" name="last_name" value={values.last_name} onChange={change}
              error={errors.last_name} maxLength={100} autoComplete="family-name" />
            <TextField label="Date of birth" name="date_of_birth" type="date" max={todayISO()}
              value={values.date_of_birth} onChange={change} error={errors.date_of_birth} autoComplete="bday" />
            <SelectField label="Sex" name="sex" value={values.sex} onChange={change} error={errors.sex}
              placeholder="Choose" options={SEX_OPTIONS} />
            <TextField label={<>National ID <span className="field__optional">(optional)</span></>}
              name="national_id" inputMode="numeric" maxLength={14} value={values.national_id}
              onChange={change} error={errors.national_id} />
            <TextField label="Phone" name="phone" type="tel" inputMode="numeric" maxLength={SIGNUP_PHONE_LENGTH}
              value={values.phone} onChange={change} error={errors.phone} autoComplete="tel"
              // hint="11 digits, numbers only."
               />
            <TextField className="form-grid__full" label="Email" name="email" type="email" maxLength={254}
              value={values.email} onChange={change} error={errors.email} autoComplete="email"
              // hint="Used for notifications and to reset your password. You sign in with your username."
               />
            <TextField className="form-grid__full" label="Username" name="username" maxLength={150}
              value={values.username} onChange={change} error={errors.username} autoComplete="username"
              autoCapitalize="none" spellCheck={false} hint="Letters, numbers and @ . + - _ only." />
            <PasswordField label="Password" name="password" value={values.password} onChange={change}
              error={errors.password} autoComplete="new-password" />
            <PasswordField label="Confirm password" name="confirmPassword" value={values.confirmPassword}
              onChange={change} error={errors.confirmPassword} autoComplete="new-password" />
          </div>

          <Button type="submit" block loading={saving}>
            {saving ? 'Creating account…' : 'Create account'}
          </Button>
        </form>
      </AuthLayout>
    </div>
  )
}
