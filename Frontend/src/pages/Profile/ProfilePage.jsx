import { useState } from 'react'
import { changePassword, getErrorMessage, updateMe } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import { useAuth } from '../../auth/authContext'
import { displayName, ROLE_LABELS, roleLine } from '../../auth/roles'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PageHeader from '../../components/ui/PageHeader'
import Panel from '../../components/ui/Panel'
import PasswordField from '../../components/ui/PasswordField'
import TextField from '../../components/ui/TextField'
import { formatDateTime } from '../../utils/format'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function ContactForm() {
  const { user, reloadUser } = useAuth()
  const isStaff = Boolean(user.staff_profile)
  const [values, setValues] = useState({ email: user.email || '', phone: user.staff_profile?.phone || '' })
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(null)
  const [saving, setSaving] = useState(false)

  const change = (event) => {
    setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))
    setMessage(null)
  }

  const submit = async (event) => {
    event.preventDefault()
    const email = values.email.trim()
    if (email && !EMAIL_PATTERN.test(email)) {
      setErrors({ email: 'Enter a valid email address.' })
      return
    }
    setErrors({})
    setSaving(true)
    try {
      await updateMe(isStaff ? { email, phone: values.phone.trim() } : { email })
      await reloadUser()
      setMessage({ type: 'success', text: 'Contact details saved.' })
    } catch (error) {
      const { form, ...rest } = fieldErrors(error)
      setErrors(rest)
      setMessage({ type: 'error', text: form || getErrorMessage(error, 'Could not save your details.') })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack">
      {message && <Alert variant={message.type}>{message.text}</Alert>}
      <TextField label="Email" name="email" type="email" value={values.email} onChange={change}
        error={errors.email} maxLength={254}
        hint="Used for notifications and to reset your password. You sign in with your username." />
      {isStaff && (
        <TextField label="Phone" name="phone" type="tel" value={values.phone} onChange={change}
          error={errors.phone} maxLength={20} />
      )}
      <div className="form-actions">
        <Button type="submit" loading={saving}>Save contact details</Button>
      </div>
    </form>
  )
}

function PasswordForm() {
  const { signOut } = useAuth()
  const [values, setValues] = useState({ current: '', next: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!values.current) next.current = 'Enter your current password.'
    if (!values.next) next.next = 'Enter a new password.'
    else if (values.next.length < 8) next.next = 'Use at least 8 characters.'
    if (values.next && values.confirm !== values.next) next.confirm = 'The passwords do not match.'
    setErrors(next)
    setFormError('')
    if (Object.keys(next).length) return
    setSaving(true)
    try {
      await changePassword({ currentPassword: values.current, newPassword: values.next })
      // The backend revoked every session; sign in again with the new password.
      await signOut('password_changed')
    } catch (error) {
      const fields = fieldErrors(error)
      setErrors({ current: fields.current_password, next: fields.new_password })
      setFormError(fields.form || (fields.current_password || fields.new_password ? ''
        : getErrorMessage(error, 'Could not change your password.')))
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="form-stack">
      {formError && <Alert variant="error">{formError}</Alert>}
      <PasswordField label="Current password" name="current" value={values.current} onChange={change}
        error={errors.current} autoComplete="current-password" />
      <PasswordField label="New password" name="next" value={values.next} onChange={change}
        error={errors.next} autoComplete="new-password"
        hint="At least 8 characters; not too common or similar to your username." />
      <PasswordField label="Confirm new password" name="confirm" value={values.confirm} onChange={change}
        error={errors.confirm} autoComplete="new-password" />
      <div className="form-actions">
        <Button type="submit" loading={saving}>Change password</Button>
      </div>
      <p className="muted-text">You will be signed out on all devices and asked to sign in again.</p>
    </form>
  )
}

export default function ProfilePage() {
  const { user } = useAuth()
  return (
    <>
      <PageHeader eyebrow="Account" title="My profile" />
      <div className="content-grid content-grid--even">
        <div className="content-stack">
          <Panel title="Account">
            <dl className="detail-list">
              <div><dt>Name</dt><dd>{displayName(user)}</dd></div>
              <div><dt>Username</dt><dd>{user.username}</dd></div>
              <div><dt>Role</dt><dd>{ROLE_LABELS[user.role]}</dd></div>
              <div><dt>Job title</dt><dd>{user.role === 'patient' ? '—' : roleLine(user)}</dd></div>
              {user.staff_profile && (
                <>
                  <div><dt>Department</dt><dd>{user.staff_profile.department || '—'}</dd></div>
                  <div><dt>License number</dt><dd>{user.staff_profile.license_no || '—'}</dd></div>
                </>
              )}
              <div><dt>Last sign-in</dt><dd>{formatDateTime(user.last_login)}</dd></div>
            </dl>
            <p className="muted-text panel-note">
              Your name, role and job title are managed by the system administrator.
            </p>
          </Panel>
          <Panel title="Contact details">
            <ContactForm />
          </Panel>
        </div>
        <Panel title="Change password">
          <PasswordForm />
        </Panel>
      </div>
    </>
  )
}
