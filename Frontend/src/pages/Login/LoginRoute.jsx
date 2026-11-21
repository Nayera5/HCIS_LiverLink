import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/authContext'
import FullPageSpinner from '../../components/ui/FullPageSpinner'
import LoginPage from './LoginPage'

const SIGN_OUT_NOTICES = {
  inactivity: 'For patient privacy, you were signed out after 15 minutes without activity.',
  expired: 'Your session has ended. Please sign in again.',
  password_changed: 'Your password was changed. Sign in with your new password.',
  signed_out: 'You have signed out.',
}

/** /login: connects the Login page to the session and returns the user where they were going. */
export default function LoginRoute() {
  const { status, signIn, signOutReason } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const from = location.state?.from?.pathname || '/'

  if (status === 'loading') return <FullPageSpinner label="Loading…" />
  if (status === 'authenticated') return <Navigate to={from} replace />

  return (
    <LoginPage
      notice={SIGN_OUT_NOTICES[signOutReason]}
      onLoginSuccess={(tokens) => {
        signIn(tokens)
          .then(() => navigate(from, { replace: true }))
          .catch(() => {})
      }}
    />
  )
}
