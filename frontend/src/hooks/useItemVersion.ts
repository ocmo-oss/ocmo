import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export function isLatestVersionRef(versionRef: string | undefined): boolean {
  return versionRef === undefined || versionRef === 'latest'
}

export function useItemVersion() {
  const [searchParams, setSearchParams] = useSearchParams()

  const versionRef = useMemo(() => {
    const tag = searchParams.get('tag')
    const version = searchParams.get('version')
    return tag ?? version ?? undefined
  }, [searchParams])

  const setVersionRef = useCallback((ref: string | null) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.delete('version')
      next.delete('tag')
      if (ref) {
        if (/^\d+$/.test(ref)) {
          next.set('version', ref)
        } else {
          next.set('tag', ref)
        }
      }
      return next
    }, { replace: true })
  }, [setSearchParams])

  const clearVersionRef = useCallback(() => setVersionRef(null), [setVersionRef])

  return {
    versionRef,
    isPinned: versionRef !== undefined,
    setVersionRef,
    clearVersionRef,
  }
}
