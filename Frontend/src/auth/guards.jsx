import { Navigate, Outlet, useLocation } from 'react-router-dom'
import FullPageSpinner from '../components/ui/FullPageSpinner'
import ForbiddenPage from '../pages/Errors/ForbiddenPage'
import { useAuth } from './authContext'

/** Renders child routes only for a signed-in user; otherwise sends them to /login. */
export function RequireAuth() {
  const { status, signOutReason } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <FullPageSpinner label="Loading your workspace…" />
  if (status !== 'authenticated') {
    // Return to the requested page only when the session ended on its own (or the user was never
    // signed in). After an explicit sign-out the next person starts from their own dashboard.
    const keepTarget = !signOutReason || signOutReason === 'expired' || signOutReason === 'inactivity'
    return <Navigate to="/login" replace state={keepTarget ? { from: location } : undefined} />
  }
  return <Outlet />
}

/**
 * Renders child routes only when the user holds the capability (the backend checks too).
 * `capability` may be a list: then holding ANY of them is enough.
 */
export function RequireCapability({ capability }) {
  const { can } = useAuth()
  const allowed = Array.isArray(capability) ? capability.some(can) : can(capability)
  return allowed ? <Outlet /> : <ForbiddenPage />
}

/** Public-only pages (login, password reset): signed-in users go to the app. */
export function PublicOnly() {
  const { status } = useAuth()
  if (status === 'loading') return <FullPageSpinner label="Loading…" />
  if (status === 'authenticated') return <Navigate to="/" replace />
  return <Outlet />
}
