import { formatUserDateTimeLong } from '../../lib/datetime'
import { Trash2 } from 'lucide-react'

interface DeletedVersionNoticeProps {
  version: number
  deletedAt: string
  deletedBy: string
}

export function DeletedVersionNotice({ version, deletedAt, deletedBy }: DeletedVersionNoticeProps) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/20">
          <Trash2 className="h-5 w-5 text-red-500" />
        </div>
        <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Version {version} was deleted
        </h2>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Deleted by <span className="font-mono text-gray-700 dark:text-gray-300">{deletedBy}</span>
          {' '}on{' '}
          <time dateTime={deletedAt} className="text-gray-700 dark:text-gray-300">
            {formatUserDateTimeLong(deletedAt)}
          </time>
        </p>
        <p className="mt-3 text-xs text-gray-400">
          Content for this version is no longer available.
        </p>
      </div>
    </div>
  )
}
