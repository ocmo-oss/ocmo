import { useCallback, useEffect, useRef } from 'react'
import { useBeforeUnload, useBlocker } from 'react-router-dom'

/**
 * Prompt the user before navigating away or closing the tab when dirty=true.
 * Call `allowNavigationOnce()` immediately before intentional programmatic navigation
 * (e.g. after a successful save) to skip the confirmation dialog.
 */
export function useDirtyGuard(dirty: boolean) {
  const allowNavigationRef = useRef(false)

  const allowNavigationOnce = useCallback(() => {
    allowNavigationRef.current = true
  }, [])

  // Native browser close/refresh
  useBeforeUnload(
    (event) => {
      if (dirty && !allowNavigationRef.current) {
        event.preventDefault()
        // Legacy support
        event.returnValue = ''
      }
    },
    { capture: true },
  )

  // React Router in-app navigation
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }: { currentLocation: { pathname: string }; nextLocation: { pathname: string } }) => {
      if (allowNavigationRef.current) {
        allowNavigationRef.current = false
        return false
      }
      return dirty && currentLocation.pathname !== nextLocation.pathname
    },
  )

  useEffect(() => {
    if (blocker.state === 'blocked') {
      const ok = window.confirm('You have unsaved changes. Leave anyway?')
      if (ok) {
        blocker.proceed()
      } else {
        blocker.reset()
      }
    }
  }, [blocker])

  return { allowNavigationOnce }
}
