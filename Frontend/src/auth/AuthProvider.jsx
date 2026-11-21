import { useCallback, useEffect, useMemo, useState } from 'react'
import { getMe, logout as logoutRequest } from '../api/auth'
import { setSessionExpiredHandler } from '../api/http'
import { AuthContext } from './authContext'
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from './tokenStorage'
import { useIdleTimeout } from './useIdleTimeout'

const IDLE_TIMEOUT_MS = 15 * 60 * 1000 // spec §1: automatic logout after inactivity

export default function AuthProvider({ children }) {
  const [status, setStatus] = useState(() => (getAccessToken() ? 'loading' : 'anonymous'))
  const [user, setUser] = useState(null)
  const [signOutReason, setSignOutReason] = useState(null)

  const endSession = useCallback((reason) => {
    clearTokens()
    setUser(null)
    setStatus('anonymous')
    setSignOutReason(reason || null)
  }, [])

  const loadUser = useCallback(async () => {
    try {
      const me = await getMe()
      setUser(me)
      setStatus('authenticated')
      return me
    } catch (error) {
      endSession(error?.status === 401 ? 'expired' : null)
      throw error
    }
  }, [endSession])

  // Restore an existing session (same tab) on first load. State is set in the promise
  // callbacks only, and ignored if the component unmounted meanwhile.
  useEffect(() => {
    if (!getAccessToken()) return undefined
    let active = true
    getMe().then(
      (me) => {
        if (!active) return
        setUser(me)
        setStatus('authenticated')
      },
      (error) => {
        if (active) endSession(error?.status === 401 ? 'expired' : null)
      },
    )
    return () => {
      active = false
    }
  }, [endSession])

  useEffect(() => {
    setSessionExpiredHandler((reason) => endSession(reason))
    return () => setSessionExpiredHandler(() => {})
  }, [endSession])

  const signIn = useCallback(
    async (tokens) => {
      saveTokens(tokens)
      setSignOutReason(null)
      return loadUser()
    },
    [loadUser],
  )

  const signOut = useCallback(
    async (reason = 'signed_out') => {
      const refresh = getRefreshToken()
      if (refresh) {
        try {
          await logoutRequest(refresh) // revoke on the server; ignore failures
        } catch {
          // The tokens are cleared locally either way.
        }
      }
      endSession(reason)
    },
    [endSession],
  )

  const idleSignOut = useCallback(() => signOut('inactivity'), [signOut])
  useIdleTimeout({ enabled: status === 'authenticated', timeoutMs: IDLE_TIMEOUT_MS, onIdle: idleSignOut })

  const value = useMemo(
    () => ({
      status,
      user,
      signOutReason,
      signIn,
      signOut,
      reloadUser: loadUser,
      can: (capability) => Boolean(user?.capabilities?.includes(capability)),
    }),
    [status, user, signOutReason, signIn, signOut, loadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
