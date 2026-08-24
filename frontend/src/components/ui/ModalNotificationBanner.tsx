import { AlertCircle, AlertTriangle, Info } from 'lucide-react'
import type { Notification, Severity } from '../../store/notifications'
import { formatNotificationCopy } from '../../store/notifications'
import { cn } from './cn'
import { NotificationCopyButton } from './NotificationCopyButton'

function severityIcon(s: Severity) {
  if (s === 'error') return <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
  if (s === 'warning') return <AlertTriangle className="h-4 w-4 shrink-0 text-orange-500" />
  return <Info className="h-4 w-4 shrink-0 text-blue-500" />
}

function severityStyles(s: Severity) {
  if (s === 'error') {
    return 'border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-950/40'
  }
  if (s === 'warning') {
    return 'border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950/40'
  }
  return 'border-blue-300 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/40'
}

interface ModalNotificationBannerProps {
  notification: Notification
}

export function ModalNotificationBanner({ notification }: ModalNotificationBannerProps) {
  const { severity, message, detail, auditEventId } = notification

  return (
    <div
      className={cn(
        'shrink-0 border-b px-6 py-3 text-sm',
        severityStyles(severity),
      )}
      role="alert"
    >
      <div className="flex items-start gap-2">
        {severityIcon(severity)}
        <div className="min-w-0 flex-1">
          <p className="text-gray-800 dark:text-gray-200">{message}</p>
          {detail && (
            <pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-gray-600 dark:text-gray-400">
              {detail}
            </pre>
          )}
        </div>
        <NotificationCopyButton
          getText={() => formatNotificationCopy({ message, detail, auditEventId })}
        />
      </div>
    </div>
  )
}
