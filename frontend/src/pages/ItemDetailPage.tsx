import { lazy, Suspense, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { treeApi } from '../api/tree'
import { useItemVersion } from '../hooks/useItemVersion'
import { useItemPermissions } from '../hooks/useItemPermissions'
import { Skeleton } from '../components/ui/Skeleton'
import { PermissionDenied } from '../components/items/PermissionDenied'
import { ItemRestrictedView } from '../components/items/ItemRestrictedView'
import { NamespaceWelcome } from '../components/namespace/NamespaceWelcome'
import { ApiError } from '../api/client'
import { isPermissionDeniedError } from '../components/QueryAccessGate'
import { pushApiError } from '../store/notifications'
import type { AnyExtendedNode, ItemType } from '../api/types'

const VyshyvankaNotFound = lazy(() =>
  import('../components/items/VyshyvankaNotFound').then((m) => ({ default: m.VyshyvankaNotFound })),
)

const ConfigEditor = lazy(() => import('../components/items/ConfigEditor'))
const TemplateEditor = lazy(() => import('../components/items/TemplateEditor'))
const SecretView = lazy(() => import('../components/items/SecretView'))
const ResolverView = lazy(() => import('../components/items/ResolverView'))
const FolderView = lazy(() => import('../components/items/FolderView'))

function resolveItemType(
  navigateItem: { type: ItemType } | null | undefined,
  isLeaf: boolean,
): ItemType {
  if (navigateItem?.type) return navigateItem.type
  return isLeaf ? 'config' : 'folder'
}

export function ItemDetailPage() {
  const { namespace, '*': path } = useParams<{ namespace: string; '*': string }>()
  const { versionRef } = useItemVersion()

  const {
    data: navData,
    isLoading: navLoading,
    error: navError,
  } = useQuery({
    queryKey: ['item-nav', namespace, path],
    queryFn: ({ signal }) => treeApi.navigate(namespace!, path!, {}, signal),
    enabled: !!namespace && !!path,
    staleTime: 30_000,
    retry: false,
  })

  const itemType = navData
    ? resolveItemType(navData.item, navData.is_leaf)
    : 'config'

  const permissions = useItemPermissions(
    namespace!,
    path ?? '',
    itemType,
    !!navData && !navError,
  )

  const {
    data,
    isLoading: itemLoading,
    error: itemError,
  } = useQuery({
    queryKey: ['item', namespace, path, versionRef],
    queryFn: ({ signal }) => treeApi.get(
      namespace!,
      path!,
      versionRef ? { version: versionRef } : {},
      signal,
    ),
    enabled: !!namespace && !!path && !!navData && permissions.canRead && !permissions.isLoading,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: false,
  })

  useEffect(() => {
    if (!itemError) return
    if (isPermissionDeniedError(itemError)) return
    const detail = itemError instanceof ApiError && itemError.status === 404
      ? 'Not found or no access'
      : undefined
    pushApiError('Failed to load item', itemError, detail)
  }, [itemError])

  if (!path) {
    return <NamespaceWelcome namespace={namespace!} />
  }

  if (navLoading || (navData && permissions.isLoading)) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (navError) {
    const err = navError as Error & { status?: number }
    if (err.status === 404) {
      return (
        <div className="relative h-full min-h-0">
          <Suspense fallback={null}>
            <VyshyvankaNotFound className="absolute left-5 top-0 bottom-0" />
          </Suspense>
        </div>
      )
    }
    if (err.status === 403) {
      return (
        <PermissionDenied message="You do not have permission to access this namespace." />
      )
    }
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-red-500">{err.message}</p>
      </div>
    )
  }

  if (!navData) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!permissions.canRead || (itemError && isPermissionDeniedError(itemError))) {
    return (
      <ItemRestrictedView
        namespace={namespace!}
        path={path}
        type={itemType}
        permissions={permissions}
      />
    )
  }

  if (itemLoading) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (itemError) {
    const err = itemError as Error & { status?: number }
    if (err.status === 404) {
      return (
        <div className="relative h-full min-h-0">
          <Suspense fallback={null}>
            <VyshyvankaNotFound className="absolute left-5 top-0 bottom-0" />
          </Suspense>
        </div>
      )
    }
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-red-500">{err.message}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-6 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const editor = renderEditor(data, namespace!, permissions)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Suspense fallback={<div className="p-6 space-y-3"><Skeleton className="h-8 w-64" /><Skeleton className="h-64 w-full" /></div>}>
        {editor}
      </Suspense>
    </div>
  )
}

function renderEditor(
  data: AnyExtendedNode,
  namespace: string,
  permissions: ReturnType<typeof useItemPermissions>,
) {
  switch (data.type) {
    case 'config':
      return (
        <ConfigEditor
          item={data}
          namespace={namespace}
          permissions={permissions}
        />
      )
    case 'template':
      return (
        <TemplateEditor
          item={data}
          namespace={namespace}
          permissions={permissions}
        />
      )
    case 'secret':
      return (
        <SecretView
          item={data}
          namespace={namespace}
          permissions={permissions}
        />
      )
    case 'resolver':
      return <ResolverView item={data} namespace={namespace} permissions={permissions} />
    case 'folder':
      return <FolderView item={data} namespace={namespace} permissions={permissions} />
    default:
      return (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-red-500">Unsupported item type</p>
        </div>
      )
  }
}
