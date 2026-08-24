import { useState } from 'react'
import type { ItemType } from '../../api/types'
import type { useItemPermissions } from '../../hooks/useItemPermissions'
import { isBuiltinNamespacePath } from '../../lib/builtinPaths'
import { ItemHeader } from './ItemHeader'
import { DeleteDialog } from './DeleteDialog'
import { LocationDialog } from './LocationDialog'
import { PermissionDenied } from './PermissionDenied'
import { ItemAuditTab } from './ItemAuditTab'
import { cn } from '../ui/cn'

interface ItemRestrictedViewProps {
  namespace: string
  path: string
  type: ItemType
  permissions: ReturnType<typeof useItemPermissions>
  message?: string
}

export function ItemRestrictedView({
  namespace,
  path,
  type,
  permissions,
  message = 'You do not have permission to view this item.',
}: ItemRestrictedViewProps) {
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [moveOpen, setMoveOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'content' | 'audit'>(() =>
    permissions.canAudit ? 'audit' : 'content',
  )

  const canDeleteItem = permissions.canDelete && !isBuiltinNamespacePath(path)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ItemHeader
        namespace={namespace}
        path={path}
        type={type}
        onDelete={canDeleteItem ? () => setDeleteOpen(true) : undefined}
        onMove={permissions.canMove ? () => setMoveOpen(true) : undefined}
        onCopy={permissions.canCopy ? () => setCopyOpen(true) : undefined}
      />
      {permissions.canAudit && (
        <div className="flex items-center gap-0.5 border-b px-4 dark:border-gray-700">
          <button
            type="button"
            onClick={() => setActiveTab('audit')}
            className={cn(
              'border-b-2 px-3 py-2 text-xs font-medium transition-colors',
              activeTab === 'audit'
                ? 'border-brand-500 text-brand-700 dark:text-brand-300'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400',
            )}
          >
            Audit
          </button>
        </div>
      )}
      <div className="flex min-h-0 flex-1 flex-col">
        {activeTab === 'content' && <PermissionDenied message={message} />}
        {activeTab === 'audit' && permissions.canAudit && (
          <ItemAuditTab namespace={namespace} path={path} type={type} />
        )}
      </div>
      <DeleteDialog
        namespace={namespace}
        path={path}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
      />
      <LocationDialog
        mode="move"
        namespace={namespace}
        path={path}
        type={type}
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
      />
      <LocationDialog
        mode="copy"
        namespace={namespace}
        path={path}
        type={type}
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
      />
    </div>
  )
}
