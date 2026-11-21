import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getLoginErrorMessage, login } from '../../api/auth'
import { saveTokens } from '../../auth/tokenStorage'
import Alert from '../../components/ui/Alert'
import Button from '../../components/ui/Button'
import PasswordField from '../../components/ui/PasswordField'
import TextField from '../../components/ui/TextField'
import { LockIcon } from '../../components/ui/icons'
import { validateLoginForm, validatePassword, validateUsername } from '../../utils/validation'
import BrandPanel from './BrandPanel'
import './LoginPage.css'

const FIELD_VALIDATORS = { username: validateUsername, password: validatePassword }

/**
 * @param {function} [onLoginSuccess]  Called with the token pair after a successful sign-in.
 *   When routing exists, the parent uses it to go to the user's dashboard.
 * @param {string} [forgotPasswordHref]
 * @param {string} [registerHref]
 * @param {string} [notice]  Information shown above the form (e.g. signed out after inactivity).
 */
export default function LoginPage({
  onLoginSuccess,
  forgotPasswordHref = '/forgot-password',
  registerHref = '/register',
  notice,
}) {
  const [values, setValues] = useState({ username: '', password: '' })
  const [errors, setErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [status, setStatus] = useState('idle') // idle | submitting | success
  const [formError, setFormError] = useState('')

  const usernameRef = useRef(null)
  const passwordRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => () => abortRef.current?.abort(), [])

  const submitting = status === 'submitting'

  function handleChange(event) {
    const { name, value } = event.target
    setValues((prev) => ({ ...prev, [name]: value }))
    if (formError) setFormError('')
    // Once a field has been checked, re-check it as the user fixes it.
    if (touched[name]) {
      setErrors((prev) => ({ ...prev, [name]: FIELD_VALIDATORS[name](value) }))
    }
  }

  function handleBlur(event) {
    const { name, value } = event.target
    // Don't nag about an empty field the user just tabbed through.
    if (!value && !touched[name]) return
    setTouched((prev) => ({ ...prev, [name]: true }))
    setErrors((prev) => ({ ...prev, [name]: FIELD_VALIDATORS[name](value) }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return

    const nextErrors = validateLoginForm(values)
    setErrors(nextErrors)
    setTouched({ username: true, password: true })
    if (nextErrors.username) {
      usernameRef.current?.focus()
      return
    }
    if (nextErrors.password) {
      passwordRef.current?.focus()
      return
    }

    setStatus('submitting')
    setFormError('')
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const tokens = await login(
        // Username is trimmed but never lowercased: login is case-sensitive.
        { username: values.username.trim(), password: values.password },
        { signal: controller.signal },
      )
      saveTokens(tokens)
      setValues((prev) => ({ ...prev, password: '' }))
      setStatus('success')
      onLoginSuccess?.(tokens)
    } catch (error) {
      if (error.name === 'AbortError') return
      setStatus('idle')
      setFormError(getLoginErrorMessage(error))
      setValues((prev) => ({ ...prev, password: '' }))
      passwordRef.current?.focus()
    }
  }

  return (
    <div className="login-page">
      <BrandPanel />

      <main className="login-main">
        <div className="login-main__inner">
          <header className="login-header">
            <h1 className="login-header__title">Sign in</h1>
            {/* <p className="login-header__subtitle">
              Staff, patients and donors use the same sign-in. You will see the pages for your
              role.
            </p> */}
          </header>

          <section className="login-card" aria-label="Sign in form">
            <form className="login-form" onSubmit={handleSubmit} noValidate>
              {notice && !formError && status !== 'success' && <Alert variant="info">{notice}</Alert>}
              {formError && <Alert variant="error">{formError}</Alert>}
              {status === 'success' && (
                <Alert variant="success">You are signed in.</Alert>
              )}

              <TextField
                ref={usernameRef}
                label="Username"
                name="username"
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                maxLength={150}
                placeholder="Enter your username"
                value={values.username}
                onChange={handleChange}
                onBlur={handleBlur}
                error={errors.username}
                disabled={submitting}
                required
              />

              <PasswordField
                ref={passwordRef}
                label="Password"
                labelAction={
                  <Link className="login-link" to={forgotPasswordHref}>
                    Forgot password?
                  </Link>
                }
                name="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                value={values.password}
                onChange={handleChange}
                onBlur={handleBlur}
                error={errors.password}
                disabled={submitting}
                required
              />

              <Button type="submit" block loading={submitting}>
                {submitting ? 'Signing in…' : 'Sign in'}
              </Button>
{/* 
              <Alert variant="info">
                For patient privacy, you are signed out automatically after 15 minutes without
                activity.
              </Alert> */}
            </form>
          </section>

          <section className="register-card" aria-labelledby="register-title">
            <h2 id="register-title" className="register-card__title">
              New patient or living donor?
            </h2>
            <p className="register-card__text">Register to book visits and see your results.</p>
            <Button as={Link} to={registerHref} variant="outline" className="register-card__cta">
              Create account
            </Button>
          </section>

          {/* <p className="login-footnote">Staff accounts are created by the system administrator.</p> */}

          <p className="login-security">
            <LockIcon size={14} />
            <span>Encrypted connection · Every record access is logged</span>
          </p>
        </div>
      </main>
    </div>
  )
}
