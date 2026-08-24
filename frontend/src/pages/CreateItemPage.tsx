import { lazy, Suspense, useMemo } from 'react'
import { Navigate, useParams, useSearchParams } from 'react-router-dom'
import {
  isCreateableItemType,
  normalizePathSegment,
  stubConfigNode,
  stubResolverNode,
  stubSecretNode,
  stubTemplateNode,
} from '../lib/createItemStubs'
import { useCreateItemPath } from '../lib/createItemPath'
import { validateTreePathCharacters } from '../lib/locationPath'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { useItemPermissions } from '../hooks/useItemPermissions'
import { CreateItemPathHeader } from '../components/items/CreateItemPathHeader'
import { Skeleton } from '../components/ui/Skeleton'
import { PermissionDenied } from '../components/items/PermissionDenied'
import { pathSegments } from '../lib/paths'

const ConfigEditor = lazy(() => import('../components/items/ConfigEditor'))
const TemplateEditor = lazy(() => import('../components/items/TemplateEditor'))
const SecretView = lazy(() => import('../components/items/SecretView'))
const ResolverView = lazy(() => import('../components/items/ResolverView'))

const PERMISSIONS_DEBOUNCE_MS = 400

export function CreateItemPage() {
  const { namespace, type } = useParams<{ namespace: string; type: string }>()
  const [searchParams] = useSearchParams()
  const parentPath = normalizePathSegment(searchParams.get('in') ?? '')

  const {
    prefixSegments,
    currentInput,
    fullPath,
    initialParentSegments,
    onInputChange,
    onInputKeyDown,
  } = useCreateItemPath(parentPath)

  const validType = type && isCreateableItemType(type) ? type : null

  function resolveCreatePathError(path: string, hasInput: boolean): string | undefined {
    if (!hasInput) {
      return undefined
    }
    return validateTreePathCharacters(path)
      ?? (path.length === 0 || pathSegments(path).length === 0 ? 'Enter a valid path' : undefined)
  }

  const pathError = resolveCreatePathError(fullPath, currentInput.trim().length > 0)

  const debouncedFullPath = useDebouncedValue(fullPath, PERMISSIONS_DEBOUNCE_MS)
  const debouncedPathError = resolveCreatePathError(
    debouncedFullPath,
    currentInput.trim().length > 0,
  )

  const permissions = useItemPermissions(
    namespace ?? '',
    debouncedFullPath,
    validType ?? 'config',
    Boolean(validType && namespace && debouncedFullPath && !debouncedPathError),
  )

  const item = useMemo(() => {
    if (!validType || !fullPath) {
      return null
    }
    switch (validType) {
      case 'config':
        return stubConfigNode(fullPath)
      case 'template':
        return stubTemplateNode(fullPath)
      case 'secret':
        return stubSecretNode(fullPath)
      case 'resolver':
        return stubResolverNode(fullPath)
    }
  }, [validType, fullPath])

  if (!validType) {
    return <Navigate to={`/ns/${namespace}/configs`} replace />
  }

  const editor = (() => {
    if (!item || !namespace) return null
    switch (validType) {
      case 'config':
        return <ConfigEditor item={item} namespace={namespace} permissions={permissions} mode="create" />
      case 'template':
        return <TemplateEditor item={item} namespace={namespace} permissions={permissions} mode="create" />
      case 'secret':
        return <SecretView item={item} namespace={namespace} permissions={permissions} mode="create" />
      case 'resolver':
        return <ResolverView item={item} namespace={namespace} permissions={permissions} mode="create" />
    }
  })()

  const showPermissionDenied = Boolean(
    fullPath
    && !pathError
    && debouncedFullPath === fullPath
    && !permissions.isLoading
    && !permissions.canWrite,
  )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <CreateItemPathHeader
        namespace={namespace ?? ''}
        type={validType}
        prefixSegments={prefixSegments}
        initialParentSegments={initialParentSegments}
        currentInput={currentInput}
        onInputChange={onInputChange}
        onInputKeyDown={onInputKeyDown}
        error={pathError}
      />

      <div className="flex min-h-0 flex-1 flex-col">
        {!fullPath ? (
          <div className="flex flex-1 items-center justify-center text-sm text-gray-400">
            Enter a path to continue
          </div>
        ) : showPermissionDenied ? (
          <PermissionDenied message="You do not have permission to create this item." />
        ) : (
          <Suspense fallback={
            <div className="p-6 space-y-3">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-64 w-full" />
            </div>
          }>
            {editor}
          </Suspense>
        )}
      </div>
    </div>
  )
}
