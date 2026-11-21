import { ApiError, apiRequest } from './client'
import { authRequest } from './http'

/**
 * Sign in with username + password against SimpleJWT's TokenObtainPairView
 * (POST /api/auth/token/).
 *
 * accounts.User keeps Django's standard USERNAME_FIELD = 'username', so SimpleJWT
 * expects the body { username, password }. Email is not a login identifier.
 *
 * @returns {Promise<{access: string, refresh: string}>}
 */
export function login({ username, password }, { signal } = {}) {
  return apiRequest('/auth/token/', {
    method: 'POST',
    body: { username, password },
    signal,
  })
}

/** Server-side logout: blacklists the refresh token. */
export function logout(refresh) {
  return authRequest('/auth/logout/', { method: 'POST', body: { refresh } })
}

/** The signed-in user: role, job title and capabilities. */
export function getMe() {
  return authRequest('/auth/me/')
}

/** Update own contact details: { email?, phone? } (phone: staff only). */
export function updateMe(changes) {
  return authRequest('/auth/me/', { method: 'PATCH', body: changes })
}

export function changePassword({ currentPassword, newPassword }) {
  return authRequest('/auth/change-password/', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
  })
}

export function requestPasswordReset(email) {
  return apiRequest('/auth/password-reset/', { method: 'POST', body: { email } })
}

export function confirmPasswordReset({ uid, token, newPassword }) {
  return apiRequest('/auth/password-reset/confirm/', {
    method: 'POST',
    body: { uid, token, new_password: newPassword },
  })
}

/**
 * Turn any login failure into a message that is safe and clear to show.
 * Never reveals whether the username exists.
 */
export function getLoginErrorMessage(error) {
  if (!(error instanceof ApiError)) {
    return 'Something went wrong. Please try again.'
  }
  if (error.isNetworkError) {
    return 'We could not reach the server. Check your connection and try again.'
  }
  if (error.status === 401) {
    return 'Incorrect username or password, or the account is inactive.'
  }
  if (error.status === 429) {
    return 'Too many sign-in attempts. Please wait a moment and try again.'
  }
  if (error.status >= 500) {
    return 'The server had a problem signing you in. Please try again shortly.'
  }
  return 'Sign-in is not available right now. Please try again later.'
}

/** Generic, safe message for any other API failure. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (!(error instanceof ApiError)) return fallback
  if (error.isNetworkError) return 'We could not reach the server. Check your connection and try again.'
  if (error.status === 403) return 'You do not have permission to do this.'
  if (error.status === 404) return 'This item could not be found.'
  if (error.status === 429) return 'Too many attempts. Please wait a while and try again.'
  if (error.status >= 500) return 'The server had a problem. Please try again shortly.'
  return error.data?.detail || fallback
}
