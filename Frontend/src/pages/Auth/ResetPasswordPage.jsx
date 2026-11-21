import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { confirmPasswordReset, getErrorMessage } from '../../api/auth'
import { fieldErrors } from '../../api/http'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PasswordField from '../../components/ui/PasswordField'
import AuthLayout from './AuthLayout'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''
  const [values, setValues] = useState({ next: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [done, setDone] = useState('')
  const [saving, setSaving] = useState(false)

  const footer = (
    <p className="login-footnote">
      <Link className="login-link" to="/login">Back to sign in</Link>
    </p>
  )

  if (!uid || !token) {
    return (
      <AuthLayout title="Reset your password" footer={footer}>
        <div className="login-form">
          <Alert variant="error">This password reset link is incomplete. Please use the link from your email.</Alert>
          <Button as={Link} to="/forgot-password" variant="outline" block>Request a new link</Button>
        </div>
      </AuthLayout>
    )
  }

  const change = (event) => setValues((prev) => ({ ...prev, [event.target.name]: event.target.value }))

  const submit = async (event) => {
    event.preventDefault()
    const next = {}
    if (!values.next) next.next = 'Enter a new password.'
    else if (values.next.length < 8) next.next = 'Use at least 8 characters.'
    if (values.next && values.confirm !== values.next) next.confirm = 'The passwords do not match.'
    setErrors(next)
    setFormError('')
    if (Object.keys(next).length) return
    setSaving(true)
    try {
      const data = await confirmPasswordReset({ uid, token, newPassword: values.next })
      setDone(data.detail)
    } catch (error) {
      const fields = fieldErrors(error)
      setErrors({ next: fields.new_password })
      setFormError(fields.new_password ? '' : fields.form || getErrorMessage(error, 'Could not reset your password.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <AuthLayout title="Choose a new password" subtitle="Your new password replaces the old one immediately." footer={footer}>
      {done ? (
        <div className="login-form">
          <Alert variant="success">{done}</Alert>
          <Button as={Link} to="/login" block>Sign in</Button>
        </div>
      ) : (
        <form className="login-form" onSubmit={submit} noValidate>
          {formError && <Alert variant="error">{formError}</Alert>}
          <PasswordField label="New password" name="next" value={values.next} onChange={change}
            error={errors.next} autoComplete="new-password" disabled={saving}
            hint="At least 8 characters; not too common or similar to your username." />
          <PasswordField label="Confirm new password" name="confirm" value={values.confirm} onChange={change}
            error={errors.confirm} autoComplete="new-password" disabled={saving} />
          <Button type="submit" block loading={saving}>
            {saving ? 'Saving…' : 'Save new password'}
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
