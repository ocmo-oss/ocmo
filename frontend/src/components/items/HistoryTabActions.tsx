import { useMutation, useQueryClient } from '@tanstack/react-query'
import { GitCompare, Tag, Trash2 } from 'lucide-react'

import { treeApi } from '../../api/tree'
import type { HistorySelectionItem } from '../../hooks/useHistorySelection'
import { Button } from '../ui/Button'
import { invalidateItemDetailQueries } from '../../lib/treeQuery'
import { pushApiError } from '../../store/notifications'
import { showToast } from '../ui/Toast'

interface HistoryTabActionsProps {
  namespace: string
  path: string
  selected: HistorySelectionItem[]
  canDiff: boolean
  canUntag: boolean
  canRemove: boolean
  canTag: boolean
  canDelete: boolean
  diffOpen: boolean
  onDiff: () => void
  onClearSelection: () => void
}

export function HistoryTabActions({
  namespace,
  path,
  selected,
  canDiff,
  canUntag,
  canRemove,
  canTag,
  canDelete,
  diffOpen,
  onDiff,
  onClearSelection,
}: HistoryTabActionsProps) {
  const qc = useQueryClient()

  const untagMut = useMutation({
    mutationFn: async () => {
      const tags = selected.filter(s => s.kind === 'tag' && s.tagName)
      await Promise.all(tags.map(s => treeApi.deleteTag(namespace, path, s.tagName!)))
    },
    onSuccess: () => {
      invalidateItemDetailQueries(qc, namespace, path)
      showToast('Tag(s) removed')
      onClearSelection()
    },
    onError: (e: Error) => pushApiError('Untag failed', e),
  })

  const removeMut = useMutation({
    mutationFn: async () => {
      const versions = selected.filter(s => s.kind === 'version')
      await Promise.all(
        versions.map(s => treeApi.delete(namespace, path, { preview: false, version: s.version })),
      )
    },
    onSuccess: () => {
      invalidateItemDetailQueries(qc, namespace, path)
      showToast('Version(s) removed')
      onClearSelection()
    },
    onError: (e: Error) => pushApiError('Remove failed', e),
  })

  return (
    <div className="flex items-center gap-1">
      {canTag && (
        <Button
          variant="ghost"
          size="sm"
          disabled={diffOpen || !canUntag}
          loading={untagMut.isPending}
          onClick={() => untagMut.mutate()}
          title="Remove selected tag(s)"
        >
          <Tag className="h-3.5 w-3.5" />
          Untag
        </Button>
      )}
      {canDelete && (
        <Button
          variant="ghost"
          size="sm"
          disabled={diffOpen || !canRemove}
          loading={removeMut.isPending}
          onClick={() => removeMut.mutate()}
          title="Delete selected version(s)"
        >
          <Trash2 className="h-3.5 w-3.5 text-red-500" />
          Remove
        </Button>
      )}
      <Button
        variant="secondary"
        size="sm"
        disabled={diffOpen || !canDiff}
        onClick={onDiff}
        title="Compare two selected versions"
      >
        <GitCompare className="h-3.5 w-3.5" />
        Diff
      </Button>
    </div>
  )
}
