import { useEffect, useRef } from 'react'

const ACTIVITY_EVENTS = ['pointerdown', 'keydown', 'wheel', 'touchstart', 'scroll']

/**
 * Calls `onIdle` after `timeoutMs` without user activity. Activity in the page resets the timer;
 * the check also runs when the tab becomes visible again (timers are throttled in background tabs).
 */
export function useIdleTimeout({ enabled, timeoutMs, onIdle }) {
  const onIdleRef = useRef(onIdle)

  useEffect(() => {
    onIdleRef.current = onIdle
  }, [onIdle])

  useEffect(() => {
    if (!enabled) return undefined
    let lastActivity = Date.now()
    let timer = null

    const check = () => {
      if (Date.now() - lastActivity >= timeoutMs) {
        onIdleRef.current()
      } else {
        timer = window.setTimeout(check, timeoutMs - (Date.now() - lastActivity))
      }
    }
    const markActive = () => {
      lastActivity = Date.now()
    }
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        window.clearTimeout(timer)
        check()
      }
    }

    timer = window.setTimeout(check, timeoutMs)
    ACTIVITY_EVENTS.forEach((name) => window.addEventListener(name, markActive, { passive: true }))
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.clearTimeout(timer)
      ACTIVITY_EVENTS.forEach((name) => window.removeEventListener(name, markActive))
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [enabled, timeoutMs])
}
