import { useCallback, useEffect, useMemo, useState } from 'react'
import { normalizePathSegment } from './createItemStubs'
import { splitTreePathSuffixInput } from './locationPath'
import { pathSegments } from './paths'

export function buildCreateItemPath(prefixSegments: string[], currentInput: string): string {
  const parts = [...prefixSegments]
  const tail = normalizePathSegment(currentInput)
  if (tail) {
    parts.push(tail)
  }
  return parts.join('/')
}

export function applyCreatePathInput(
  prefixSegments: string[],
  _currentInput: string,
  nextInput: string,
): { prefixSegments: string[]; currentInput: string } {
  const { completedSegments, currentInput } = splitTreePathSuffixInput(nextInput)
  if (completedSegments.length === 0) {
    return { prefixSegments, currentInput }
  }

  return {
    prefixSegments: [...prefixSegments, ...completedSegments],
    currentInput,
  }
}

export function popCreatePathSegment(
  prefixSegments: string[],
): { prefixSegments: string[]; currentInput: string } | null {
  if (prefixSegments.length === 0) {
    return null
  }

  const popped = prefixSegments[prefixSegments.length - 1] ?? ''
  return {
    prefixSegments: prefixSegments.slice(0, -1),
    currentInput: popped,
  }
}

export function isNavigableCreatePathSegment(
  index: number,
  prefixSegments: string[],
  initialParentSegments: string[],
): boolean {
  if (index >= initialParentSegments.length) {
    return false
  }
  return prefixSegments.slice(0, index + 1).every((segment, i) => segment === initialParentSegments[i])
}

export function useCreateItemPath(initialParentPath: string) {
  const initialParentSegments = useMemo(
    () => pathSegments(normalizePathSegment(initialParentPath)),
    [initialParentPath],
  )
  const [prefixSegments, setPrefixSegments] = useState(initialParentSegments)
  const [currentInput, setCurrentInput] = useState('')

  useEffect(() => {
    setPrefixSegments(initialParentSegments)
    setCurrentInput('')
  }, [initialParentSegments])

  const fullPath = useMemo(
    () => buildCreateItemPath(prefixSegments, currentInput),
    [prefixSegments, currentInput],
  )

  const onInputChange = useCallback((value: string) => {
    setPrefixSegments(prev => {
      const next = applyCreatePathInput(prev, '', value)
      setCurrentInput(next.currentInput)
      return next.prefixSegments
    })
  }, [])

  const onInputKeyDown = useCallback((event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'Backspace' || event.currentTarget.value !== '') {
      return
    }

    setPrefixSegments(prev => {
      const popped = popCreatePathSegment(prev)
      if (!popped) {
        return prev
      }

      event.preventDefault()
      setCurrentInput(popped.currentInput)
      return popped.prefixSegments
    })
  }, [])

  return {
    prefixSegments,
    currentInput,
    fullPath,
    initialParentSegments,
    onInputChange,
    onInputKeyDown,
  }
}
