import { ShieldAlert } from 'lucide-react'

export function PermissionDenied({ message }: { message: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <ShieldAlert className="h-10 w-10 text-gray-300 dark:text-gray-600" />
      <p className="max-w-md text-sm text-gray-500 dark:text-gray-400">{message}</p>
    </div>
  )
}
