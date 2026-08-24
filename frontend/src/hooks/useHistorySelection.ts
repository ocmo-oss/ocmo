import { useCallback, useMemo, useState } from 'react'

export interface HistorySelectionItem {
  key: string
  kind: 'version' | 'tag'
  label: string
  version: number
  tagName?: string
}

export function useHistorySelection() {
  const [selected, setSelected] = useState<HistorySelectionItem[]>([])

  const toggle = useCallback((item: HistorySelectionItem) => {
    setSelected(prev => {
      const exists = prev.some(s => s.key === item.key)
      if (exists) return prev.filter(s => s.key !== item.key)
      if (prev.length >= 2) return [prev[1]!, item]
      return [...prev, item]
    })
  }, [])

  const clear = useCallback(() => setSelected([]), [])

  const isSelected = useCallback(
    (key: string) => selected.some(s => s.key === key),
    [selected],
  )

  const selectedTags = useMemo(
    () => selected.filter(s => s.kind === 'tag'),
    [selected],
  )

  const selectedVersions = useMemo(
    () => selected.filter(s => s.kind === 'version'),
    [selected],
  )

  return {
    selected,
    selectedTags,
    selectedVersions,
    toggle,
    clear,
    isSelected,
    canDiff: selected.length === 2,
    canUntag: selectedTags.length > 0 && !selectedTags.some(t => t.tagName === 'latest'),
    canRemove: selectedVersions.length > 0,
  }
}
