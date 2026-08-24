import type { ReactNode } from 'react'
import { cn } from './cn'

type TooltipSide = 'top' | 'bottom' | 'left' | 'right'
type TooltipAlign = 'start' | 'center' | 'end'

const sideAlignClasses: Record<TooltipSide, Record<TooltipAlign, string>> = {
  top: {
    start: 'bottom-full left-0 mb-1',
    center: 'bottom-full left-1/2 mb-1 -translate-x-1/2',
    end: 'bottom-full right-0 mb-1',
  },
  bottom: {
    start: 'top-full left-0 mt-1',
    center: 'top-full left-1/2 mt-1 -translate-x-1/2',
    end: 'top-full right-0 mt-1',
  },
  left: {
    start: 'right-full top-0 mr-1',
    center: 'right-full top-1/2 mr-1 -translate-y-1/2',
    end: 'right-full bottom-0 mr-1',
  },
  right: {
    start: 'left-full top-0 ml-1',
    center: 'left-full top-1/2 ml-1 -translate-y-1/2',
    end: 'left-full bottom-0 ml-1',
  },
}

export function Tooltip({
  content,
  children,
  className,
  side = 'top',
  align = 'center',
  open,
  showOnHover = true,
}: {
  content: ReactNode
  children: ReactNode
  className?: string
  side?: TooltipSide
  align?: TooltipAlign
  /** When true, force the tooltip visible (e.g. keyboard shortcut hint). */
  open?: boolean
  /** When false, the tooltip is only shown while `open` is true. */
  showOnHover?: boolean
}) {
  return (
    <span className={cn('group/tooltip relative inline-flex', className)}>
      {children}
      <span
        role="tooltip"
        className={cn(
          'pointer-events-none absolute z-50 w-max max-w-xs rounded border bg-surface-elevated px-2 py-1.5 text-[11px] leading-snug text-gray-600 shadow-md',
          'dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300',
          open
            ? 'block'
            : showOnHover
              ? 'hidden group-hover/tooltip:block'
              : 'hidden',
          sideAlignClasses[side][align],
        )}
      >
        {content}
      </span>
    </span>
  )
}
