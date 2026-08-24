import { ServerCrash } from 'lucide-react'

export function ApiUnavailable({ message }: { message?: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <ServerCrash className="h-10 w-10 text-gray-300 dark:text-gray-600" />
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">API unavailable</p>
      <p className="max-w-md text-sm text-gray-500 dark:text-gray-400">
        {message ?? 'The API is temporarily unavailable. Try again in a moment.'}
      </p>
    </div>
  )
}
