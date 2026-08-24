import { Badge } from '../components/ui/Badge'
import { cn } from '../components/ui/cn'
import { useReservedTags } from '../store/health'
import { isReservedTagName } from '../store/versionBootstrap'

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info'

export function tagBadgeVariant(name: string, reservedTags?: { config: string[]; template: string[]; secret: string[] }): BadgeVariant {
  if (name === 'latest') return 'info'
  if (name === 'stable') return 'success'
  if (reservedTags && isReservedTagName(name, reservedTags)) return 'info'
  return 'default'
}

export function TagBadge({
  name,
  className,
}: {
  name: string
  className?: string
}) {
  const reservedTags = useReservedTags()
  return (
    <Badge variant={tagBadgeVariant(name, reservedTags)} className={cn('text-[11px] px-1.5 py-0', className)}>
      {name}
    </Badge>
  )
}

export function VersionBadge({
  version,
  className,
}: {
  version: number
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-1.5 py-0 font-mono text-[11px] font-medium',
        'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
        className,
      )}
    >
      v{version}
    </span>
  )
}
