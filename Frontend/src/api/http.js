// Authenticated requests: adds the access token, and on a 401 refreshes it once and retries.
// Refresh tokens rotate (the backend returns a new one each time), so the new pair is saved.
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from '../auth/tokenStorage'
import { ApiError, apiRequest } from './client'

let refreshing = null
let sessionExpiredHandler = () => {}

/** Called by the AuthProvider so an unrecoverable 401 signs the user out of the UI. */
export function setSessionExpiredHandler(handler) {
  sessionExpiredHandler = handler
}

function refreshAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) return Promise.reject(new ApiError('No session', { status: 401 }))
  // Several requests may hit 401 together: share one refresh call.
  if (!refreshing) {
    refreshing = apiRequest('/auth/token/refresh/', { method: 'POST', body: { refresh } })
      .then((data) => {
        saveTokens({ access: data.access, refresh: data.refresh || refresh })
        return data.access
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

export async function authRequest(path, options = {}) {
  const send = (token) =>
    apiRequest(path, { ...options, headers: { ...options.headers, Authorization: `Bearer ${token}` } })

  const access = getAccessToken()
  try {
    if (!access) throw new ApiError('Not signed in', { status: 401 })
    return await send(access)
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error
    let freshAccess
    try {
      freshAccess = await refreshAccessToken()
    } catch {
      clearTokens()
      sessionExpiredHandler('expired')
      throw error
    }
    return send(freshAccess)
  }
}

/** Build "?a=1&b=2" from an object, skipping empty values. */
export function toQuery(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  const text = query.toString()
  return text ? `?${text}` : ''
}

/**
 * Field errors from a DRF 400 response, flattened to { field: 'message' } plus `form` for
 * non-field errors and `detail`.
 */
export function fieldErrors(error) {
  const data = error instanceof ApiError ? error.data : null
  if (!data || typeof data !== 'object') return {}
  const out = {}
  Object.entries(data).forEach(([key, value]) => {
    const message = Array.isArray(value) ? value.join(' ') : typeof value === 'string' ? value : ''
    if (!message) return
    out[key === 'non_field_errors' || key === 'detail' ? 'form' : key] = message
  })
  return out
}
