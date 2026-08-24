import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { treeApi } from '../../api/tree'
import { parseDeletePreviewLines } from '../../lib/deletePreview'
import { ItemIcon } from '../../lib/itemTypes'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { pushApiError } from '../../store/notifications'
import { showToast } from '../ui/Toast'
import { refreshTreeQueries } from '../../lib/treeQuery'

interface DeleteDialogProps {
  namespace: string
  path: string
  open: boolean
  onClose: () => void
}

export function DeleteDialog({ namespace, path, open, onClose }: DeleteDialogProps) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [previewResult, setPreviewResult] = useState<string[] | null>(null)

  const previewMut = useMutation({
    mutationFn: () => treeApi.delete(namespace, path, { preview: true }),
    onSuccess: result => setPreviewResult(result.delete),
    onError: (e: Error) => pushApiError('Preview failed', e),
  })

  const deleteMut = useMutation({
    mutationFn: () => treeApi.delete(namespace, path, { preview: false }),
    onSuccess: async () => {
      await refreshTreeQueries(qc, namespace, path)
      void qc.removeQueries({ queryKey: ['item', namespace, path] })
      void qc.removeQueries({ queryKey: ['versions', namespace, path] })
      showToast(`Deleted "${path}"`)
      onClose()
      navigate(`/ns/${namespace}/configs`)
    },
    onError: (e: Error) => pushApiError('Delete failed', e),
  })

  useEffect(() => {
    if (!open) return
    setPreviewResult(null)
    previewMut.mutate()
  }, [open, namespace, path])

  const previewItems = useMemo(
    () => (previewResult ? parseDeletePreviewLines(previewResult) : []),
    [previewResult],
  )

  const handleClose = () => {
    setPreviewResult(null)
    onClose()
  }

  const loading = previewMut.isPending
  const ready = previewResult !== null

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Delete item"
      size="md"
      footer={
        <>
          <Button variant="ghost" onClick={handleClose}>Cancel</Button>
          <Button
            variant="danger"
            loading={deleteMut.isPending}
            disabled={!ready || loading}
            onClick={() => deleteMut.mutate()}
          >
            {ready
              ? `Confirm delete (${previewItems.length} item${previewItems.length !== 1 ? 's' : ''})`
              : 'Confirm delete'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Deleting <strong className="font-mono">{path}</strong> in namespace{' '}
          <strong className="font-mono">{namespace}</strong>. This action cannot be undone.
        </p>

        {loading && (
          <p className="text-xs text-gray-400">Loading impact preview…</p>
        )}

        {previewMut.isError && !loading && (
          <p className="text-xs text-red-500">Failed to load impact preview. Close and try again.</p>
        )}

        {ready && (
          <div>
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Will delete {previewItems.length} item{previewItems.length !== 1 ? 's' : ''}:
            </p>
            <ul className="max-h-48 overflow-auto space-y-1 rounded border p-2 dark:border-gray-700">
              {previewItems.map(item => (
                <li
                  key={`${item.type}:${item.path}`}
                  className="flex items-center gap-2 rounded px-1 py-0.5"
                >
                  <ItemIcon type={item.type} size="sm" />
                  <span className="min-w-0 truncate font-mono text-xs text-gray-600 dark:text-gray-400">
                    {item.path}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Modal>
  )
}
