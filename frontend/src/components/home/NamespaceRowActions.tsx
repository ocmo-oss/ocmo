import { Link } from 'react-router-dom'
import { Settings, Shield, Trash2 } from 'lucide-react'
import { useNamespacePermissions } from '../../hooks/useNamespacePermissions'
import { permissionsConfigPath } from '../../lib/builtinPaths'

interface NamespaceRowActionsProps {
  namespace: string
  onDelete: () => void
}

export function NamespaceRowActions({ namespace, onDelete }: NamespaceRowActionsProps) {
  const { isLoading, canWrite, canDelete } = useNamespacePermissions(namespace)

  if (isLoading) {
    return <span className="inline-block h-7 w-20" />
  }

  if (!canWrite && !canDelete) {
    return null
  }

  return (
    <div className="flex items-center justify-end gap-1">
      {canWrite && (
        <Link
          to={`/ns/${namespace}/settings`}
          className="rounded p-1.5 text-gray-400 hover:bg-slate-200 hover:text-gray-600 dark:hover:bg-gray-700"
          title="Namespace settings"
        >
          <Settings className="h-4 w-4" />
        </Link>
      )}
      {canWrite && (
        <Link
          to={`/ns/${namespace}/configs/${permissionsConfigPath()}`}
          className="rounded p-1.5 text-gray-400 hover:bg-slate-200 hover:text-gray-600 dark:hover:bg-gray-700"
          title="Edit permissions"
        >
          <Shield className="h-4 w-4" />
        </Link>
      )}
      {canDelete && (
        <button
          type="button"
          onClick={onDelete}
          className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
          title="Delete namespace"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
