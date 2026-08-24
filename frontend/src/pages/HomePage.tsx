import { useMemo, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, ClipboardList, Shield } from 'lucide-react'
import { formatUserDateTimeRelative } from '../lib/datetime'
import { namespacesApi } from '../api/namespaces'
import { useAuth } from '../auth/useAuth'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Modal } from '../components/ui/Modal'
import { Skeleton } from '../components/ui/Skeleton'
import { QueryAccessGate } from '../components/QueryAccessGate'
import { pushApiError } from '../store/notifications'
import { showToast } from '../components/ui/Toast'
import type { Namespace } from '../api/types'
import { DefaultNamespaceToggle } from '../components/home/DefaultNamespaceToggle'
import { useDefaultNamespace } from '../store/defaultNamespace'
import { NamespaceRowActions } from '../components/home/NamespaceRowActions'
import { useCanCreateNamespace } from '../hooks/useCanCreateNamespace'

function CreateNamespaceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  const mut = useMutation({
    mutationFn: () => namespacesApi.create({ name: name.trim(), description }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['namespaces'] })
      showToast(`Namespace "${name}" created`)
      onClose()
      setName('')
      setDescription('')
    },
    onError: (e: Error) => {
      setError(e.message)
      pushApiError('Failed to create namespace', e)
    },
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create namespace"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={mut.isPending} onClick={() => mut.mutate()}>
            Create
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label="Name"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="my-namespace"
          error={error}
          autoFocus
        />
        <Input
          label="Description"
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Optional description"
        />
      </div>
    </Modal>
  )
}

function DeleteNamespaceModal({
  ns,
  open,
  onClose,
}: {
  ns: Namespace | null
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const { namespace: defaultNamespace, clearDefaultNamespace } = useDefaultNamespace()
  const [confirm, setConfirm] = useState('')

  const mut = useMutation({
    mutationFn: () => namespacesApi.delete(ns!.name),
    onSuccess: () => {
      if (defaultNamespace === ns!.name) {
        clearDefaultNamespace()
      }
      void qc.invalidateQueries({ queryKey: ['namespaces'] })
      showToast(`Namespace "${ns!.name}" deleted`)
      onClose()
      setConfirm('')
    },
    onError: (e: Error) => pushApiError('Failed to delete namespace', e),
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Delete namespace"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            variant="danger"
            loading={mut.isPending}
            disabled={confirm !== ns?.name}
            onClick={() => mut.mutate()}
          >
            Delete permanently
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          This will permanently delete <strong className="font-mono">{ns?.name}</strong> and all
          its configs, templates, secrets, and resolvers. This action cannot be undone.
        </p>
        <Input
          label={`Type "${ns?.name}" to confirm`}
          value={confirm}
          onChange={e => setConfirm(e.target.value)}
          placeholder={ns?.name}
        />
      </div>
    </Modal>
  )
}

export function HomePage() {
  const navigate = useNavigate()
  const { isGlobalAdmin } = useAuth()
  const { canCreate: canCreateNamespace, isLoading: createPermLoading } = useCanCreateNamespace()
  const { namespace: defaultNamespace } = useDefaultNamespace()
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Namespace | null>(null)
  const [filter, setFilter] = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['namespaces', filter],
    queryFn: ({ signal }) =>
      namespacesApi.list({ name_filter: filter || undefined, limit: 50 }, signal),
    staleTime: 30_000,
  })

  const namespaces = useMemo(() => {
    const items = data?.items ?? []
    if (!defaultNamespace) return items
    return [...items].sort((a, b) => {
      if (a.name === defaultNamespace) return -1
      if (b.name === defaultNamespace) return 1
      return 0
    })
  }, [data?.items, defaultNamespace])

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Namespaces</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Select a namespace to start managing configs
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isGlobalAdmin && (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate('/audit')}>
                <ClipboardList className="h-4 w-4" />
                Global audit
              </Button>
              <Button variant="ghost" size="sm" onClick={() => navigate('/permissions/global')}>
                <Shield className="h-4 w-4" />
                Global permissions
              </Button>
            </>
          )}
          {!createPermLoading && canCreateNamespace && (
            <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" />
              New namespace
            </Button>
          )}
        </div>
      </div>

      <div className="mb-4">
        <Input
          placeholder="Filter namespaces…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      <QueryAccessGate
        isLoading={isLoading}
        isError={isError}
        error={error}
        hasData={!!data}
        permissionDeniedMessage="You do not have permission to list namespaces."
        loadingFallback={null}
      >
      {!isLoading && data?.items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-400 p-12 text-center dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {filter ? `No namespaces matching "${filter}"` : 'No namespaces yet'}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Access is controlled by Global Permissions. Contact your platform administrator if you
            expect to see namespaces here.
          </p>
        </div>
      )}

      {!isLoading && data && data.items.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-300 dark:border-gray-700">
          <table className="min-w-full divide-y divide-slate-300 dark:divide-gray-700">
            <thead className="bg-surface dark:bg-gray-800/50">
              <tr>
                <th className="w-10 px-2 py-2.5" aria-label="Default namespace" />
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500">Name</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500 hidden sm:table-cell">Description</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500 hidden md:table-cell">Created</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500 hidden md:table-cell">Updated</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-surface-elevated dark:divide-gray-800 dark:bg-gray-900">
              {namespaces.map(ns => (
                <tr
                  key={ns.name}
                  className="hover:bg-slate-100 dark:hover:bg-gray-800/50"
                >
                  <td className="px-2 py-3">
                    <DefaultNamespaceToggle namespace={ns.name} />
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/ns/${ns.name}/configs`}
                      className="font-mono text-sm font-medium text-brand-700 hover:underline dark:text-brand-300"
                    >
                      {ns.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
                      {ns.description || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400 hidden md:table-cell">
                    {formatUserDateTimeRelative(ns.created_at)}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400 hidden md:table-cell">
                    {formatUserDateTimeRelative(ns.updated_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <NamespaceRowActions namespace={ns.name} onDelete={() => setDeleteTarget(ns)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </QueryAccessGate>

      <CreateNamespaceModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <DeleteNamespaceModal
        ns={deleteTarget}
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
      />
    </div>
  )
}
