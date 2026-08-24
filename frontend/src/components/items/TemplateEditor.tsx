import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import MonacoEditor from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import { AlertTriangle } from 'lucide-react'
import { treeApi } from '../../api/tree'
import type { ConfigNode } from '../../api/types'
import type { useItemPermissions } from '../../hooks/useItemPermissions'
import { useItemVersion } from '../../hooks/useItemVersion'
import { useHistorySelection } from '../../hooks/useHistorySelection'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { useItemSaveShortcut } from '../../hooks/useItemSaveShortcut'
import { useMonacoEditorTheme } from '../../hooks/useMonacoEditorTheme'
import { ItemHeader } from './ItemHeader'
import { ItemDescription } from './ItemDescription'
import { ItemHistoryTab } from './ItemHistoryTab'
import { ItemAuditTab } from './ItemAuditTab'
import { HistoryTabActions } from './HistoryTabActions'
import { DeletedVersionNotice } from './DeletedVersionNotice'
import { ItemSaveButton } from './ItemSaveButton'
import { DeleteDialog } from './DeleteDialog'
import { LocationDialog } from './LocationDialog'
import { pushApiError } from '../../store/notifications'
import { showToast } from '../ui/Toast'
import { isHealthy } from '../../store/health'
import { invalidateItemDetailQueries, invalidateTreeQueries } from '../../lib/treeQuery'
import { installEditorEmptyHint } from '../../lib/editorEmptyHint'
import {
  applyTemplateValidationMarkers,
  validateJinja2Template,
} from '../../lib/jinja2Validation'
import { cn } from '../ui/cn'
import type { ItemEditorMode } from '../../lib/itemEditorMode'
import { isCreateMode } from '../../lib/itemEditorMode'

type Tab = 'editor' | 'history' | 'audit'

const TEMPLATE_PLACEHOLDER = 'Type Jinja2 template or raw text'
const VALIDATION_DEBOUNCE_MS = 300

function selectionToDiffRef(item: { kind: string; tagName?: string; version: number }) {
  if (item.kind === 'tag' && item.tagName) return item.tagName
  return String(item.version)
}

export default function TemplateEditor({
  item,
  namespace,
  permissions,
  mode = 'edit',
}: {
  item: ConfigNode
  namespace: string
  permissions: ReturnType<typeof useItemPermissions>
  mode?: ItemEditorMode
}) {
  const creating = isCreateMode(mode)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { versionRef } = useItemVersion()
  const {
    selected: historySelected,
    toggle: toggleHistory,
    isSelected: isHistorySelected,
    clear: clearHistorySelection,
    canDiff,
    canUntag,
    canRemove,
  } = useHistorySelection()
  const [activeTab, setActiveTab] = useState<Tab>('editor')
  const [content, setContent] = useState(item.content ?? '')
  const [isDirty, setIsDirty] = useState(false)
  const [diffPair, setDiffPair] = useState<{ from: string; to: string } | null>(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [moveOpen, setMoveOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const monacoRef = useRef<typeof import('monaco-editor') | null>(null)
  const emptyHintDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const saveShortcutMountRef = useRef<
    (editorInstance: editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => void
  >(() => {})
  const debouncedContent = useDebouncedValue(content, VALIDATION_DEBOUNCE_MS)
  const monacoTheme = useMonacoEditorTheme()

  const validation = useMemo(
    () => validateJinja2Template(debouncedContent),
    [debouncedContent],
  )

  const applyValidationMarkers = useCallback((value: string) => {
    const editorInstance = editorRef.current
    const monaco = monacoRef.current
    const model = editorInstance?.getModel()
    if (!editorInstance || !monaco || !model) return
    applyTemplateValidationMarkers(model, monaco, validateJinja2Template(value))
  }, [])

  useEffect(() => {
    if (creating) return
    setContent(item.content ?? '')
    setIsDirty(false)
  }, [creating, item.path, item.version, item.content])

  useEffect(() => {
    if (activeTab !== 'history') {
      clearHistorySelection()
      setDiffPair(null)
    }
  }, [activeTab, clearHistorySelection])

  useEffect(() => {
    applyValidationMarkers(debouncedContent)
  }, [debouncedContent, applyValidationMarkers])

  useEffect(() => () => {
    emptyHintDisposableRef.current?.dispose()
  }, [])

  const handleEditorMount = (
    editorInstance: editor.IStandaloneCodeEditor,
    monaco: typeof import('monaco-editor'),
  ) => {
    editorRef.current = editorInstance
    monacoRef.current = monaco
    emptyHintDisposableRef.current?.dispose()
    emptyHintDisposableRef.current = installEditorEmptyHint(editorInstance, monaco, {
      text: TEMPLATE_PLACEHOLDER,
    })
    saveShortcutMountRef.current(editorInstance, monaco)
    applyValidationMarkers(editorInstance.getModel()?.getValue() ?? content)
  }

  const saveMut = useMutation({
    mutationFn: () =>
      item.version === 0
        ? treeApi.createTemplate(namespace, item.path, content)
        : treeApi.updateTemplate(namespace, item.path, content),
    onSuccess: () => {
      const wasNew = item.version === 0
      invalidateItemDetailQueries(qc, namespace, item.path)
      invalidateTreeQueries(qc, namespace, item.path)
      if (wasNew) {
        navigate(`/ns/${namespace}/configs/${item.path}`)
      }
      showToast(wasNew ? 'Template created' : 'Template saved')
      setIsDirty(false)
    },
    onError: (e: Error) => pushApiError('Save failed', e),
  })

  const canSave = permissions.canWrite
    && validation.valid
    && (item.version === 0 || isDirty)
    && isHealthy()

  const saveShortcut = useItemSaveShortcut({
    canSave,
    onSave: () => saveMut.mutate(),
  })
  saveShortcutMountRef.current = saveShortcut.onEditorMount

  const tabs: Array<{ id: Tab; label: string }> = creating
    ? [{ id: 'editor', label: 'Editor' }]
    : [
        { id: 'editor', label: 'Editor' },
        { id: 'history', label: 'History' },
        ...(permissions.canAudit ? [{ id: 'audit' as const, label: 'Audit' }] : []),
      ]

  const handleDiff = () => {
    if (historySelected.length !== 2) return
    const [a, b] = historySelected
    setDiffPair({
      from: selectionToDiffRef(a),
      to: selectionToDiffRef(b),
    })
  }

  const handleDiffWithCurrent = (otherRef: string) => {
    const current = versionRef ?? 'latest'
    setDiffPair({ from: otherRef, to: current })
  }

  const isDeleted = Boolean(item.deleted_at)
  const canDeleteItem = permissions.canDelete
  const canMoveItem = permissions.canMove
  const canCopyItem = permissions.canCopy

  return (
    <div className="flex h-full flex-col">
      {!creating && (
        <>
          <ItemHeader
            namespace={namespace}
            path={item.path}
            type="template"
            version={item.version}
            tags={item.tags}
            showVersionSelector
            deletedAt={item.deleted_at}
            onDelete={canDeleteItem && !isDeleted ? () => setDeleteOpen(true) : undefined}
            onMove={canMoveItem && !isDeleted ? () => setMoveOpen(true) : undefined}
            onCopy={canCopyItem && !isDeleted ? () => setCopyOpen(true) : undefined}
          />
          <ItemDescription
            namespace={namespace}
            path={item.path}
            description={item.description}
            canEdit={permissions.canDescribe}
          />
        </>
      )}
      <div className={cn(
        'flex items-center gap-0.5 border-b px-4 dark:border-gray-700',
        creating && 'py-2',
      )}>
        {!creating && tabs.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={cn('border-b-2 px-3 py-2 text-xs font-medium',
              activeTab === t.id ? 'border-brand-500 text-brand-700 dark:text-brand-300' : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400')}
          >{t.label}</button>
        ))}
        <div className="flex-1" />
        {isDirty && activeTab === 'editor' && !isDeleted && (
          <span className="mr-2 flex items-center gap-1 text-xs text-yellow-600 dark:text-yellow-400">
            <AlertTriangle className="h-3 w-3" /> Unsaved
          </span>
        )}
        {activeTab === 'history' ? (
          <HistoryTabActions
            namespace={namespace}
            path={item.path}
            selected={historySelected}
            canDiff={canDiff}
            canUntag={canUntag}
            canRemove={canRemove}
            canTag={permissions.canTag}
            canDelete={canDeleteItem}
            diffOpen={diffPair !== null}
            onDiff={handleDiff}
            onClearSelection={clearHistorySelection}
          />
        ) : activeTab === 'audit' ? null : !isDeleted && permissions.canWrite ? (
          <ItemSaveButton
            label={creating ? 'Create' : 'Save'}
            loading={saveMut.isPending}
            disabled={!canSave}
            onClick={() => saveMut.mutate()}
            buttonRef={saveShortcut.buttonRef}
            showEnterHint={saveShortcut.showEnterHint}
            enterHint={saveShortcut.enterHint}
            onKeyDown={saveShortcut.handleButtonKeyDown}
          />
        ) : null}
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {activeTab === 'editor' && isDeleted && item.deleted_at && (
          <DeletedVersionNotice
            version={item.version}
            deletedAt={item.deleted_at}
            deletedBy={item.updater}
          />
        )}
        {activeTab === 'editor' && !isDeleted && (
          <MonacoEditor
            height="100%"
            language="jinja2"
            theme={monacoTheme}
            value={content}
            onMount={handleEditorMount}
            onChange={v => {
              const next = v ?? ''
              setContent(next)
              setIsDirty(true)
              applyValidationMarkers(next)
            }}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              wordWrap: 'on',
              readOnly: !permissions.canWrite,
              accessibilitySupport: 'on',
            }}
          />
        )}
        {activeTab === 'history' && (
          <ItemHistoryTab
            namespace={namespace}
            path={item.path}
            itemType="template"
            currentVersion={item.version}
            canTag={permissions.canTag}
            isSelected={isHistorySelected}
            onToggle={toggleHistory}
            onDiffWithCurrent={handleDiffWithCurrent}
            diffPair={diffPair}
            onCloseDiff={() => setDiffPair(null)}
            onSwapDiff={() => setDiffPair(p => p && { from: p.to, to: p.from })}
          />
        )}
        {activeTab === 'audit' && (
          <ItemAuditTab namespace={namespace} path={item.path} type="template" />
        )}
      </div>

      <DeleteDialog
        namespace={namespace}
        path={item.path}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
      />

      <LocationDialog
        mode="move"
        namespace={namespace}
        path={item.path}
        type="template"
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
      />

      <LocationDialog
        mode="copy"
        namespace={namespace}
        path={item.path}
        type="template"
        tags={item.tags}
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
      />
    </div>
  )
}
