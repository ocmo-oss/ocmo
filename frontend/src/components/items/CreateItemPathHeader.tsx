import { Link } from 'react-router-dom'
import type { CreateableItemType } from '../../lib/createItemStubs'
import { isNavigableCreatePathSegment } from '../../lib/createItemPath'
import { ITEM_TYPE_LABELS, ItemIcon } from '../../lib/itemTypes'
import { cn } from '../ui/cn'

interface CreateItemPathHeaderProps {
  namespace: string
  type: CreateableItemType
  prefixSegments: string[]
  initialParentSegments: string[]
  currentInput: string
  onInputChange: (value: string) => void
  onInputKeyDown: (event: React.KeyboardEvent<HTMLInputElement>) => void
  error?: string
}

export function CreateItemPathHeader({
  namespace,
  type,
  prefixSegments,
  initialParentSegments,
  currentInput,
  onInputChange,
  onInputKeyDown,
  error,
}: CreateItemPathHeaderProps) {
  const placeholder = prefixSegments.length > 0 ? 'my-item' : 'path/to/my-item'

  return (
    <div className="shrink-0 border-b px-6 py-4 dark:border-gray-700">
      <div className="mb-3 flex items-center gap-2">
        <ItemIcon type={type} />
        <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          New {ITEM_TYPE_LABELS[type]}
        </h1>
      </div>

      <div className="space-y-1">
        <label htmlFor="create-item-path-suffix" className="block text-xs font-medium text-gray-500 dark:text-gray-400">
          Path
        </label>
        <div
          className={cn(
            'flex min-w-0 flex-wrap items-center gap-1 rounded-md border px-3 py-2',
            'bg-surface-elevated dark:bg-gray-800',
            error
              ? 'border-red-500 focus-within:ring-1 focus-within:ring-red-500'
              : 'border-slate-400 focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500 dark:border-gray-600',
          )}
        >
          {prefixSegments.map((seg, i) => {
            const segPath = prefixSegments.slice(0, i + 1).join('/')
            const navigable = isNavigableCreatePathSegment(i, prefixSegments, initialParentSegments)

            return (
              <span key={`${segPath}-${i}`} className="flex items-center text-xs text-gray-400">
                {i > 0 && <span className="font-mono text-gray-400" aria-hidden="true">/</span>}
                {navigable ? (
                  <Link
                    to={`/ns/${namespace}/configs/${segPath}`}
                    className="font-mono hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {seg}
                  </Link>
                ) : (
                  <span className="font-mono text-gray-500 dark:text-gray-400">{seg}</span>
                )}
              </span>
            )
          })}
          {prefixSegments.length > 0 && (
            <span className="font-mono text-gray-400" aria-hidden="true">/</span>
          )}
          <input
            id="create-item-path-suffix"
            value={currentInput}
            onChange={e => onInputChange(e.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder={placeholder}
            autoFocus
            spellCheck={false}
            className={cn(
              'min-w-[8rem] flex-1 bg-transparent font-mono text-sm text-gray-900 outline-none',
              'placeholder:text-gray-400 dark:text-gray-100 dark:placeholder:text-gray-500',
            )}
          />
        </div>
        {error ? (
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
        ) : (
          <p className="text-xs text-gray-400">
            Type <span className="font-mono">/</span> to add a folder segment. Press Backspace on an empty field to edit earlier segments.
          </p>
        )}
      </div>
    </div>
  )
}
