// Stores the JWT pair for the current browser tab.
// sessionStorage is cleared when the tab closes, which suits a clinical system.
// Every access is wrapped because storage can be unavailable (private mode, blocked site data).

const ACCESS_KEY = 'liverlink.access'
const REFRESH_KEY = 'liverlink.refresh'

export function saveTokens({ access, refresh }) {
  try {
    sessionStorage.setItem(ACCESS_KEY, access)
    sessionStorage.setItem(REFRESH_KEY, refresh)
  } catch {
    // Storage unavailable: the session will simply not survive a reload.
  }
}

export function getAccessToken() {
  try {
    return sessionStorage.getItem(ACCESS_KEY)
  } catch {
    return null
  }
}

export function getRefreshToken() {
  try {
    return sessionStorage.getItem(REFRESH_KEY)
  } catch {
    return null
  }
}

export function clearTokens() {
  try {
    sessionStorage.removeItem(ACCESS_KEY)
    sessionStorage.removeItem(REFRESH_KEY)
  } catch {
    // Nothing to clear.
  }
}
