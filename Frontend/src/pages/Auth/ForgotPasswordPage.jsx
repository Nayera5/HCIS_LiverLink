import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getErrorMessage, requestPasswordReset } from '../../api/auth'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import TextField from '../../components/ui/TextField'
import AuthLayout from './AuthLayout'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [sent, setSent] = useState('')
  const [sending, setSending] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    const value = email.trim()
    if (!value) return setError('Enter the email address on your account.')
    if (!EMAIL_PATTERN.test(value)) return setError('Enter a valid email address, like name@example.com.')
    setError('')
    setFormError('')
    setSending(true)
    try {
      const data = await requestPasswordReset(value)
      setSent(data.detail)
    } catch (err) {
      setFormError(getErrorMessage(err, 'Could not send the reset link. Please try again.'))
    } finally {
      setSending(false)
    }
  }

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter the email address on your account. We will send you a link to choose a new password."
      footer={
        <p className="login-footnote">
          <Link className="login-link" to="/login">Back to sign in</Link>
        </p>
      }
    >
      {sent ? (
        <div className="login-form">
          <Alert variant="success">{sent}</Alert>
          <p className="login-header__subtitle">
            The link expires automatically. If nothing arrives, check the address or contact the
            hospital administrator. Accounts without an email address are reset by the administrator.
          </p>
        </div>
      ) : (
        <form className="login-form" onSubmit={submit} noValidate>
          {formError && <Alert variant="error">{formError}</Alert>}
          <TextField label="Email address" name="email" type="email" inputMode="email" autoComplete="email"
            value={email} onChange={(event) => setEmail(event.target.value)} error={error}
            placeholder="name@example.com" disabled={sending} />
          <Button type="submit" block loading={sending}>
            {sending ? 'Sending…' : 'Send reset link'}
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
