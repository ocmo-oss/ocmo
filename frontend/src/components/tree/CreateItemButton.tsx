import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import {
  CREATEABLE_ITEM_TYPES,
  type CreateableItemType,
} from '../../lib/createItemStubs'
import { useCreateParentPath } from '../../hooks/useCreateParentPath'
import { useItemPermissions } from '../../hooks/useItemPermissions'
import { useNamespacePermissions } from '../../hooks/useNamespacePermissions'
import { ItemIcon, ITEM_TYPE_LABELS } from '../../lib/itemTypes'
import { Tooltip } from '../ui/Tooltip'
import { cn } from '../ui/cn'

export function CreateItemButton() {
  const { namespace } = useParams<{ namespace: string }>()
  const navigate = useNavigate()
  const parentPath = useCreateParentPath()
  const [open, setOpen] = useState(false)
  const nsPermissions = useNamespacePermissions(namespace)
  const parentPermissions = useItemPermissions(
    namespace ?? '',
    parentPath,
    'folder',
    !!namespace && !!parentPath,
  )

  const canCreate = parentPath
    ? parentPermissions.canWrite
    : nsPermissions.canWrite

  const openCreateForm = (type: CreateableItemType) => {
    if (!namespace) return
    const params = new URLSearchParams()
    if (parentPath) params.set('in', parentPath)
    const qs = params.toString()
    navigate(`/ns/${namespace}/configs/new/${type}${qs ? `?${qs}` : ''}`)
    setOpen(false)
  }

  if (nsPermissions.isLoading || (parentPath && parentPermissions.isLoading)) {
    return null
  }

  if (!canCreate) {
    return null
  }

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={cn(
          'flex h-8 w-8 items-center justify-center rounded-md border border-slate-300 bg-surface-elevated text-gray-600',
          'hover:border-brand-400 hover:text-brand-700',
          'dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-brand-500 dark:hover:text-brand-300',
          open && 'border-brand-400 text-brand-700 dark:border-brand-500 dark:text-brand-300',
        )}
        aria-label="Create new item"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <Plus className="h-4 w-4" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div
            role="menu"
            className="absolute right-0 top-full z-40 mt-1 rounded-lg border bg-surface-elevated p-1.5 shadow-lg dark:border-gray-700 dark:bg-gray-900"
          >
            <div className="flex items-center gap-1">
              {CREATEABLE_ITEM_TYPES.map(type => (
                <Tooltip key={type} content={ITEM_TYPE_LABELS[type]} side="bottom" className="items-center">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => openCreateForm(type)}
                    className="flex h-8 w-8 items-center justify-center rounded-md text-gray-600 hover:bg-slate-200 dark:text-gray-300 dark:hover:bg-gray-800"
                  >
                    <ItemIcon type={type} showTooltip={false} />
                  </button>
                </Tooltip>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
