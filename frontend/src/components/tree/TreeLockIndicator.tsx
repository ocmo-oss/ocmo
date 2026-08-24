import { useNavigate, useParams } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { formatUserDateTimeShort } from '../../lib/datetime'
import type { TreeLockInfo } from '../../lib/treeLocks'
import { Tooltip } from '../ui/Tooltip'
import { cn } from '../ui/cn'

export function TreeLockIndicator({ lockInfo }: { lockInfo: TreeLockInfo }) {
  const { namespace } = useParams<{ namespace: string }>()
  const navigate = useNavigate()
  const { lock, isDirect } = lockInfo

  const createdAt = formatUserDateTimeShort(lock.created_at)

  return (
    <Tooltip
      content={(
        <span className="block whitespace-normal">
          <span className="block font-medium text-gray-800 dark:text-gray-100">
            {isDirect ? 'Locked path' : 'Under lock'}
          </span>
          <span className="mt-0.5 block font-mono text-[10px] text-gray-500 dark:text-gray-400">{lock.path}</span>
          {lock.reason && (
            <span className="mt-1 block">{lock.reason}</span>
          )}
          <span className="mt-1 block text-gray-400">{createdAt}</span>
        </span>
      )}
    >
      <button
        type="button"
        onClick={e => {
          e.preventDefault()
          e.stopPropagation()
          navigate(`/ns/${namespace}/locks/${lock.path}`)
        }}
        className={cn(
          'shrink-0 rounded p-0.5 hover:bg-slate-300/80 dark:hover:bg-gray-700/80',
          isDirect ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400 dark:text-gray-500',
        )}
        aria-label={isDirect ? `Locked: ${lock.path}` : `Under lock: ${lock.path}`}
      >
        <Lock className="h-3 w-3" />
      </button>
    </Tooltip>
  )
}
