import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { treeApi } from '../../api/tree'
import type { TreeNavigationNode } from '../../api/types'
import { ItemIcon } from '../../lib/itemTypes'
import { cn } from '../ui/cn'

interface PathSearchComboboxProps {
  namespace: string
  value: string
  onInputChange: (path: string) => void
  onSelect: (item: TreeNavigationNode) => void
  label?: string
  inputId?: string
  placeholder?: string
  error?: string
  autoFocus?: boolean
  /** When set, only matching items are shown. Default: all search hits. */
  filterItem?: (item: TreeNavigationNode) => boolean
  emptyMessage?: string
  /** Sanitize free-text input before propagating (e.g. path character filter). */
  sanitizeInput?: (value: string) => string
  queryKeySuffix?: string
}

export function PathSearchCombobox({
  namespace,
  value,
  onInputChange,
  onSelect,
  label = 'Path',
  inputId,
  placeholder = 'Search by path or name…',
  error,
  autoFocus = false,
  filterItem,
  emptyMessage = 'No matching paths',
  sanitizeInput,
  queryKeySuffix = 'path-combobox',
}: PathSearchComboboxProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(value)
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [highlighted, setHighlighted] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const resolvedInputId = inputId ?? label.toLowerCase().replace(/\s+/g, '-')

  useEffect(() => {
    setQuery(value)
  }, [value])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), 300)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [open])

  const { data: results = [], isFetching } = useQuery({
    queryKey: ['tree-search', namespace, debouncedQuery, queryKeySuffix],
    queryFn: ({ signal }) =>
      treeApi.search(namespace, null, { q: debouncedQuery, limit: 30 }, signal),
    enabled: open && debouncedQuery.length > 0,
    staleTime: 10_000,
  })

  const filteredResults = useMemo(
    () => (filterItem ? results.filter(filterItem) : results),
    [results, filterItem],
  )

  useEffect(() => {
    setHighlighted(0)
  }, [debouncedQuery, filteredResults.length])

  const showDropdown = open && debouncedQuery.length > 0

  const pick = (item: TreeNavigationNode) => {
    onSelect(item)
    setOpen(false)
  }

  const onInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown' && showDropdown && filteredResults.length > 0) {
      e.preventDefault()
      setHighlighted(i => Math.min(i + 1, filteredResults.length - 1))
    } else if (e.key === 'ArrowUp' && showDropdown && filteredResults.length > 0) {
      e.preventDefault()
      setHighlighted(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && showDropdown && filteredResults[highlighted]) {
      e.preventDefault()
      pick(filteredResults[highlighted]!)
    } else if (e.key === 'Escape' && open) {
      e.preventDefault()
      e.stopPropagation()
      setOpen(false)
    }
  }

  return (
    <div ref={rootRef} className="relative space-y-1">
      <label htmlFor={resolvedInputId} className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
        <input
          id={resolvedInputId}
          type="search"
          value={query}
          onChange={e => {
            const next = sanitizeInput ? sanitizeInput(e.target.value) : e.target.value
            setQuery(next)
            onInputChange(next)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onInputKeyDown}
          placeholder={placeholder}
          autoFocus={autoFocus}
          autoComplete="off"
          className={cn(
            'w-full rounded-md border bg-surface-elevated py-1.5 pl-8 pr-3 font-mono text-sm shadow-sm',
            'text-gray-900 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500',
            'dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500',
            error
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
              : 'border-slate-400',
          )}
        />
      </div>
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}

      {showDropdown && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-60 overflow-y-auto rounded-md border bg-surface-elevated shadow-lg dark:border-gray-700 dark:bg-gray-900">
          {isFetching && (
            <p className="px-3 py-2 text-xs text-gray-400">Searching…</p>
          )}
          {!isFetching && filteredResults.length === 0 && (
            <p className="px-3 py-2 text-xs text-gray-400">{emptyMessage}</p>
          )}
          {filteredResults.map((item, idx) => (
            <button
              key={item.path}
              type="button"
              onMouseEnter={() => setHighlighted(idx)}
              onClick={() => pick(item)}
              className={cn(
                'flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-gray-800',
                idx === highlighted && 'bg-surface dark:bg-gray-800',
              )}
            >
              <ItemIcon type={item.type} size="sm" showTooltip={false} />
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-gray-800 dark:text-gray-200">
                {item.path}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
