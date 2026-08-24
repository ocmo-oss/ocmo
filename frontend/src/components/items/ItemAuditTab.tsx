import { ItemAuditTimeline } from './ItemAuditTimeline'
import type { ItemType } from '../../api/types'
import { ResolveStatsChart } from './ResolveStatsChart'

interface ItemAuditTabProps {
  namespace: string
  path: string
  type: ItemType
}

export function ItemAuditTab({ namespace, path, type }: ItemAuditTabProps) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <ResolveStatsChart namespace={namespace} path={path} type={type} />
      <div className="min-h-0 flex-1 overflow-hidden">
        <ItemAuditTimeline namespace={namespace} path={path} type={type} />
      </div>
    </div>
  )
}
