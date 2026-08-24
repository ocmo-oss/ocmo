import { useEffect, useMemo, useRef, useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { Switch } from '@headlessui/react'
import { formatUserDateTimeShort } from '../../lib/datetime'
import { ChevronDown, Search } from 'lucide-react'
import { treeApi } from '../../api/tree'
import type { TagInfo, VersionEntry } from '../../api/types'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { useItemVersion } from '../../hooks/useItemVersion'
import { Badge } from '../ui/Badge'
import { TagBadge } from '../../lib/itemBadges'
import { cn } from '../ui/cn'

const PAGE_SIZE = 25
const SEARCH_DEBOUNCE_MS = 300

const dropdownRowClass = 'px-2.5 py-1.5'
const dropdownTextClass = 'text-xs'
const dropdownMetaClass = 'text-[11px] text-gray-400'
const dropdownTagClass = 'px-1.5 py-0 text-[11px]'

interface VersionTagSelectorProps {
  namespace: string
  path: string
  currentVersion: number
  tags: TagInfo[]
  deletedAt?: string | null
  /** When set, selector is controlled (e.g. namespace settings). Use `"latest"` for latest. */
  value?: string
  onChange?: (ref: string) => void
}

type NavItem =
  | { kind: 'latest' }
  | {
      kind: 'version'
      version: number
      createdAt: string
      updater: string
      tagNames: string[]
      deletedAt: string | null
    }

function lastTagForVersion(version: number, itemTags: TagInfo[]): string | null {
  let last: string | null = null
  for (const tag of itemTags) {
    if (tag.version === version) last = tag.name
  }
  return last
}

function isVersionSelected(
  version: number,
  versionRef: string | undefined,
  currentVersion: number,
  itemTags: TagInfo[],
): boolean {
  if (!versionRef) return version === currentVersion
  if (/^\d+$/.test(versionRef)) return version === Number(versionRef)
  const tag = itemTags.find(t => t.name === versionRef)
  return tag?.version === version
}

export function VersionTagSelector({
  namespace,
  path,
  currentVersion,
  tags,
  deletedAt,
  value,
  onChange,
}: VersionTagSelectorProps) {
  const { versionRef: urlVersionRef, setVersionRef } = useItemVersion()
  const isControlled = onChange !== undefined
  const selectedRef = isControlled
    ? (value === 'latest' ? undefined : value)
    : urlVersionRef
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query, SEARCH_DEBOUNCE_MS)
  const [taggedOnly, setTaggedOnly] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const searchQuery = debouncedQuery.trim()

  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['versions', namespace, path, searchQuery],
    queryFn: ({ pageParam = 0, signal }) =>
      treeApi.versions(namespace, path, {
        limit: PAGE_SIZE,
        offset: pageParam,
        ...(searchQuery ? { q: searchQuery } : {}),
      }, signal),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.versions.length, 0)
      return loaded < lastPage.count ? loaded : undefined
    },
    staleTime: 30_000,
    enabled: open,
  })

  const versionsFromApi = useMemo(
    () => data?.pages.flatMap(page => page.versions) ?? [],
    [data],
  )

  const versions = useMemo((): VersionEntry[] => {
    const tagNamesByVersion = new Map<number, string[]>()
    for (const version of versionsFromApi) {
      tagNamesByVersion.set(version.version, [...version.tags])
    }
    for (const tag of tags) {
      const names = tagNamesByVersion.get(tag.version) ?? []
      if (!names.includes(tag.name)) {
        names.push(tag.name)
        tagNamesByVersion.set(tag.version, names)
      }
    }

    const merged = versionsFromApi.map(version => ({
      ...version,
      tags: tagNamesByVersion.get(version.version) ?? version.tags,
    }))

    if (!searchQuery && !merged.some(version => version.version === currentVersion)) {
      merged.unshift({
        version: currentVersion,
        tags: tagNamesByVersion.get(currentVersion)
          ?? tags.filter(tag => tag.version === currentVersion).map(tag => tag.name),
        updater: '',
        created_at: '',
        deleted_at: null,
        size: null,
      })
    }

    return merged
  }, [versionsFromApi, tags, currentVersion, searchQuery])

  const filteredVersions = useMemo(() => {
    if (!taggedOnly) return versions
    return versions.filter(v => v.tags.length > 0)
  }, [versions, taggedOnly])

  const navItems = useMemo<NavItem[]>(() => {
    const items: NavItem[] = []
    if (!selectedRef && !searchQuery && !taggedOnly) {
      items.push({ kind: 'latest' })
    }
    for (const version of filteredVersions) {
      items.push({
        kind: 'version',
        version: version.version,
        createdAt: version.created_at,
        updater: version.updater,
        tagNames: version.tags,
        deletedAt: version.deleted_at,
      })
    }
    return items
  }, [filteredVersions, searchQuery, taggedOnly, selectedRef])

  const label = selectedRef
    ? (/^\d+$/.test(selectedRef) ? `v${selectedRef}` : selectedRef)
    : `v${currentVersion} (latest)`

  const showDeletedBadge = Boolean(deletedAt)
  const isSearchPending = query.trim() !== searchQuery
  const showListLoading = isSearchPending || (isLoading && versionsFromApi.length === 0)

  useEffect(() => {
    if (!open) {
      setQuery('')
      setHighlighted(0)
    }
  }, [open])

  useEffect(() => {
    setHighlighted(0)
  }, [query, taggedOnly, searchQuery])

  useEffect(() => {
    setHighlighted(current => Math.min(current, Math.max(navItems.length - 1, 0)))
  }, [navItems.length])

  const scrollHighlightedIntoView = (index: number) => {
    requestAnimationFrame(() => {
      listRef.current
        ?.querySelector(`[data-nav-index="${index}"]`)
        ?.scrollIntoView({ block: 'nearest' })
    })
  }

  useEffect(() => {
    const el = listRef.current
    if (!el || !open) return

    const onScroll = () => {
      if (!hasNextPage || isFetchingNextPage) return
      if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
        void fetchNextPage()
      }
    }

    el.addEventListener('scroll', onScroll)
    return () => el.removeEventListener('scroll', onScroll)
  }, [open, hasNextPage, isFetchingNextPage, fetchNextPage])

  useEffect(() => {
    if (!open || showListLoading || isFetchingNextPage || !hasNextPage) return
    const el = listRef.current
    if (!el) return
    if (el.scrollHeight <= el.clientHeight + 4) {
      void fetchNextPage()
    }
  }, [
    open,
    showListLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    navItems.length,
    versionsFromApi.length,
  ])

  const selectRef = (ref: string | null) => {
    if (isControlled) {
      onChange(ref ?? 'latest')
    } else {
      setVersionRef(ref)
    }
    setOpen(false)
  }

  const selectVersion = (version: number) => {
    selectRef(lastTagForVersion(version, tags) ?? String(version))
  }

  const activateItem = (item: NavItem) => {
    if (item.kind === 'latest') selectRef(null)
    else selectVersion(item.version)
  }

  const onInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted(i => {
        const next = Math.min(i + 1, Math.max(navItems.length - 1, 0))
        scrollHighlightedIntoView(next)
        return next
      })
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted(i => {
        const next = Math.max(i - 1, 0)
        scrollHighlightedIntoView(next)
        return next
      })
    } else if (e.key === 'Enter' && navItems[highlighted]) {
      e.preventDefault()
      activateItem(navItems[highlighted]!)
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  let navIndex = -1

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={cn(
          'flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-mono',
          'border-slate-300 bg-surface-elevated text-gray-700 hover:border-brand-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200',
        )}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {label}
        {showDeletedBadge && <Badge variant="error">deleted</Badge>}
        <ChevronDown className="h-3 w-3 opacity-60" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-40 mt-1 w-80 rounded-lg border bg-surface-elevated shadow-lg dark:border-gray-700 dark:bg-gray-900">
            <div className="border-b p-2 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
                <input
                  ref={inputRef}
                  type="search"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={onInputKeyDown}
                  placeholder="Search versions and tags…"
                  className={cn(
                    'w-full rounded-md border border-slate-300 bg-surface-elevated py-1.5 pl-7 pr-2 text-gray-800 placeholder-gray-400 focus:border-brand-400 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200',
                    dropdownTextClass,
                  )}
                  autoFocus
                />
              </div>
              <div className={cn('mt-1.5 flex items-center justify-between gap-2', dropdownRowClass, 'px-0 py-0')}>
                <span className={cn(dropdownTextClass, 'text-gray-500 dark:text-gray-400')}>Tagged only</span>
                <Switch
                  checked={taggedOnly}
                  onChange={setTaggedOnly}
                  className={cn(
                    'relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900',
                    taggedOnly ? 'bg-brand-600' : 'bg-slate-300 dark:bg-gray-700',
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      'pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white shadow ring-0 transition',
                      taggedOnly ? 'translate-x-3' : 'translate-x-0',
                    )}
                  />
                </Switch>
              </div>
            </div>

            <div ref={listRef} className="max-h-72 overflow-y-auto" role="listbox">
              {navItems.length === 0 && !showListLoading && (
                <p className={cn(dropdownRowClass, dropdownTextClass, 'text-gray-400')}>No matching versions</p>
              )}

              {navItems.map(item => {
                navIndex += 1
                const idx = navIndex
                const active = idx === highlighted

                if (item.kind === 'latest') {
                  const selected = !selectedRef
                  return (
                    <button
                      key="latest"
                      type="button"
                      data-nav-index={idx}
                      onMouseEnter={() => setHighlighted(idx)}
                      onClick={() => selectRef(null)}
                      className={cn(
                        'flex w-full items-center justify-between text-left hover:bg-slate-100 dark:hover:bg-gray-800',
                        dropdownRowClass,
                        dropdownTextClass,
                        active && 'bg-surface dark:bg-gray-800',
                        selected && 'bg-brand-50 dark:bg-brand-900/20',
                      )}
                    >
                      <span className="font-mono text-brand-700 dark:text-brand-300">latest</span>
                      <span className={dropdownMetaClass}>v{currentVersion}</span>
                    </button>
                  )
                }

                const selected = isVersionSelected(item.version, selectedRef, currentVersion, tags)

                return (
                  <button
                    key={`v-${item.version}`}
                    type="button"
                    data-nav-index={idx}
                    onMouseEnter={() => setHighlighted(idx)}
                    onClick={() => selectVersion(item.version)}
                    className={cn(
                      'flex w-full flex-wrap items-center gap-x-2 gap-y-1 text-left hover:bg-slate-100 dark:hover:bg-gray-800',
                      dropdownRowClass,
                      dropdownTextClass,
                      active && 'bg-surface dark:bg-gray-800',
                      selected && 'bg-brand-50 dark:bg-brand-900/20',
                    )}
                  >
                    <span className={cn('shrink-0 font-mono', item.deletedAt && 'text-gray-400 line-through')}>
                      v{item.version}
                    </span>
                    {item.deletedAt && (
                      <Badge variant="error" className={dropdownTagClass}>deleted</Badge>
                    )}
                    {item.tagNames.map(tag => (
                      <TagBadge key={tag} name={tag} className={dropdownTagClass} />
                    ))}
                    <span className={cn('min-w-0 truncate', dropdownMetaClass)}>
                      {item.updater} · {formatUserDateTimeShort(item.deletedAt ?? item.createdAt)}
                    </span>
                  </button>
                )
              })}

              {showListLoading && (
                <p className={cn(dropdownRowClass, dropdownTextClass, 'text-gray-400')}>Loading…</p>
              )}

              {isFetchingNextPage && (
                <p className={cn(dropdownRowClass, dropdownTextClass, 'text-gray-400')}>Loading more…</p>
              )}

              {hasNextPage && !showListLoading && !isFetchingNextPage && (
                <button
                  type="button"
                  onClick={() => void fetchNextPage()}
                  className={cn(
                    'w-full text-left text-brand-600 hover:bg-slate-100 dark:text-brand-400 dark:hover:bg-gray-800',
                    dropdownRowClass,
                    dropdownTextClass,
                  )}
                >
                  Load older versions…
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
