import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { treeApi } from '../../api/tree'
import { VersionTagSelector } from '../items/VersionTagSelector'
import { Skeleton } from '../ui/Skeleton'

interface NamespaceConfigTagFieldProps {
  namespace: string
  path: string
  label: string
  description?: ReactNode
  value: string
  onChange: (ref: string) => void
}

export function NamespaceConfigTagField({
  namespace,
  path,
  label,
  description,
  value,
  onChange,
}: NamespaceConfigTagFieldProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['item', namespace, path, 'settings-tag-field'],
    queryFn: ({ signal }) => treeApi.get(namespace, path, {}, signal),
    enabled: !!namespace,
    staleTime: 30_000,
  })

  const config = data && data.type === 'config' ? data : null

  return (
    <div className="space-y-1">
      <div>
        <p className="text-sm font-medium leading-tight text-gray-700 dark:text-gray-300">{label}</p>
        {description && (
          <p className="text-[11px] leading-snug text-gray-400">{description}</p>
        )}
      </div>
      {isLoading || !config ? (
        <Skeleton className="h-7 w-36" />
      ) : (
        <VersionTagSelector
          namespace={namespace}
          path={path}
          currentVersion={config.version}
          tags={config.tags}
          deletedAt={config.deleted_at}
          value={value}
          onChange={onChange}
        />
      )}
    </div>
  )
}
