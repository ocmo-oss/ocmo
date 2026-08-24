import { useEffect, useState } from 'react'
import { Check, ClipboardCopy } from 'lucide-react'
import { cn } from './cn'

const COPIED_FEEDBACK_MS = 2000

interface NotificationCopyButtonProps {
  getText: () => string
  className?: string
}

export function NotificationCopyButton({ getText, className }: NotificationCopyButtonProps) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), COPIED_FEEDBACK_MS)
    return () => clearTimeout(timer)
  }, [copied])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(getText())
      setCopied(true)
    } catch {
      // clipboard unavailable
    }
  }

  return (
    <button
      type="button"
      onClick={() => { void handleCopy() }}
      className={cn(
        'shrink-0 rounded p-0.5',
        copied
          ? 'text-green-600 dark:text-green-400'
          : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-200',
        className,
      )}
      aria-label={copied ? 'Copied' : 'Copy notification'}
    >
      {copied
        ? <Check className="h-3.5 w-3.5" />
        : <ClipboardCopy className="h-3.5 w-3.5" />}
    </button>
  )
}
