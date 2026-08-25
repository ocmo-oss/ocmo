import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import MonacoEditor from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import { ChevronLeft, History, AlertTriangle, Route, RotateCcw, ScrollText } from 'lucide-react'
import { treeApi } from '../../api/tree'
import type { ConfigNode, PropagationResult } from '../../api/types'
import type { useItemPermissions } from '../../hooks/useItemPermissions'
import { isLatestVersionRef, useItemVersion } from '../../hooks/useItemVersion'
import { useHistorySelection } from '../../hooks/useHistorySelection'
import { hasManualPropagation } from '../../lib/ocmoMetadata'
import { ItemHeader } from './ItemHeader'
import { ItemDescription } from './ItemDescription'
import { ItemHistoryTab } from './ItemHistoryTab'
import { ItemAuditTab } from './ItemAuditTab'
import { HistoryTabActions } from './HistoryTabActions'
import { ResolvePanel } from '../resolve/ResolvePanel'
import { DeleteDialog } from './DeleteDialog'
import { LocationDialog } from './LocationDialog'
import { DeletedVersionNotice } from './DeletedVersionNotice'
import { ItemSaveButton } from './ItemSaveButton'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { pushApiError, pushNotification } from '../../store/notifications'
import { showToast } from '../ui/Toast'
import { isHealthy } from '../../store/health'
import { useDirtyGuard } from '../../lib/useDirtyGuard'
import { invalidateItemDetailQueries, invalidateTreeQueries } from '../../lib/treeQuery'
import { registerYamlSchemaCompletion, installYamlCompletionTriggers } from '../../lib/yamlCompletion'
import { installYamlEditorEmptyHint } from '../../lib/yamlEditorEmptyHint'
import { useMonacoEditorTheme } from '../../hooks/useMonacoEditorTheme'
import { yamlEditorOptions } from '../../lib/yamlEditorOptions'
import { useConfigYamlSchema } from '../../hooks/useConfigYamlSchema'
import { useItemSaveShortcut } from '../../hooks/useItemSaveShortcut'
import { isBuiltinNamespacePath, isBuiltinNamespaceSchemaPath } from '../../lib/builtinPaths'
import { createItemEditorModelPath } from '../../lib/configEditorSchema'
import { cn } from '../ui/cn'
import type { ItemEditorMode } from '../../lib/itemEditorMode'
import { isCreateMode, hasEditorContent } from '../../lib/itemEditorMode'

type Tab = 'editor' | 'history' | 'audit'

interface ConfigEditorProps {
  item: ConfigNode
  namespace: string
  permissions: ReturnType<typeof useItemPermissions>
  mode?: ItemEditorMode
}

function selectionToDiffRef(item: { kind: string; tagName?: string; version: number }) {
  if (item.kind === 'tag' && item.tagName) return item.tagName
  return String(item.version)
}

export default function ConfigEditor({ item, namespace, permissions, mode = 'edit' }: ConfigEditorProps) {
  const creating = isCreateMode(mode)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { versionRef, setVersionRef } = useItemVersion()
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
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [moveOpen, setMoveOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [propagateOpen, setPropagateOpen] = useState(false)
  const [resolveMounted, setResolveMounted] = useState(false)
  const [resolveOpen, setResolveOpen] = useState(false)
  const [diffPair, setDiffPair] = useState<{ from: string; to: string } | null>(null)

  const useDraftResolve = creating || isDirty
  const canEdit = permissions.canWrite && !isBuiltinNamespaceSchemaPath(item.path)
  const canDeleteItem = permissions.canDelete && !isBuiltinNamespacePath(item.path)
  const canMoveItem = permissions.canMove && !isBuiltinNamespacePath(item.path)
  const canCopyItem = permissions.canCopy && !isBuiltinNamespacePath(item.path)
  const isDeleted = Boolean(item.deleted_at)
  const { modelPath, composedSchema, metadataKey: configMetadataKey, isJsonSchemaMode } = useConfigYamlSchema({
    namespace,
    path: item.path,
    versionRef,
    editorContent: content,
    hasSavedVersion: item.version !== 0,
  })
  const canResolve = permissions.canResolve && !isJsonSchemaMode
  const showPropagate = useMemo(
    () => hasManualPropagation(content, configMetadataKey),
    [content, configMetadataKey],
  )
  const editorModelPath = creating
    ? createItemEditorModelPath(namespace, 'config')
    : modelPath
  const monacoRef = useRef<typeof import('monaco-editor') | null>(null)
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const composedSchemaRef = useRef(composedSchema)
  composedSchemaRef.current = composedSchema
  const metadataKeyRef = useRef(configMetadataKey)
  metadataKeyRef.current = configMetadataKey
  const completionDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const suggestTriggerDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const emptyHintDisposableRef = useRef<import('monaco-editor').IDisposable & { refresh: () => void } | null>(null)
  const saveShortcutMountRef = useRef<
    (editorInstance: editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => void
  >(() => {})
  const monacoTheme = useMonacoEditorTheme()

  const getUriReference = useCallback(() => {
    const metadataKey = metadataKeyRef.current
    if (!metadataKey) return null
    return {
      namespace,
      configPath: item.path,
      metadataKey,
      allowOutsideMetadata: item.path === '_permissions' || item.path === '_webhooks',
    }
  }, [namespace, item.path])

  const getParameterCompletion = useCallback(() => {
    const metadataKey = metadataKeyRef.current
    if (!metadataKey) return null
    return { metadataKey }
  }, [])

  const attachSchemaCompletion = useCallback((monaco: typeof import('monaco-editor')) => {
    completionDisposableRef.current?.dispose()
    if (!composedSchemaRef.current) return
    completionDisposableRef.current = registerYamlSchemaCompletion(
      monaco,
      () => composedSchemaRef.current,
      editorRef.current ?? undefined,
      getUriReference,
      getParameterCompletion,
    )
  }, [getUriReference, getParameterCompletion])

  const attachSuggestTriggers = useCallback((
    editorInstance: editor.IStandaloneCodeEditor,
    monaco: typeof import('monaco-editor'),
  ) => {
    suggestTriggerDisposableRef.current?.dispose()
    suggestTriggerDisposableRef.current = installYamlCompletionTriggers(
      editorInstance,
      monaco,
      () => composedSchemaRef.current,
      getUriReference,
      getParameterCompletion,
    )
  }, [getUriReference, getParameterCompletion])

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

  const { allowNavigationOnce } = useDirtyGuard(isDirty)

  const handleEditorMount = (editorInstance: editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => {
    monacoRef.current = monaco
    editorRef.current = editorInstance
    attachSchemaCompletion(monaco)
    attachSuggestTriggers(editorInstance, monaco)
    emptyHintDisposableRef.current?.dispose()
    emptyHintDisposableRef.current = installYamlEditorEmptyHint(editorInstance, monaco, {
      hasSuggestions: () => !!composedSchemaRef.current,
    })
    saveShortcutMountRef.current(editorInstance, monaco)
    return editorInstance
  }

  useEffect(() => {
    if (monacoRef.current) {
      attachSchemaCompletion(monacoRef.current)
    }
    emptyHintDisposableRef.current?.refresh()
  }, [attachSchemaCompletion, composedSchema])

  useEffect(() => () => {
    completionDisposableRef.current?.dispose()
    suggestTriggerDisposableRef.current?.dispose()
    emptyHintDisposableRef.current?.dispose()
  }, [])

  const saveMut = useMutation({
    mutationFn: async (): Promise<ConfigNode | void> => {
      if (item.version === 0) {
        await treeApi.createConfig(namespace, item.path, content)
        return
      }
      return treeApi.updateConfig(namespace, item.path, content)
    },
    onSuccess: saved => {
      const wasNew = item.version === 0
      const pinnedRef = versionRef
      invalidateItemDetailQueries(qc, namespace, item.path)
      void qc.invalidateQueries({ queryKey: ['config-data-schema', namespace, item.path] })
      invalidateTreeQueries(qc, namespace, item.path)
      if (!wasNew && saved && !isLatestVersionRef(pinnedRef)) {
        setVersionRef(String(saved.version))
      }
      if (wasNew) {
        allowNavigationOnce()
        navigate(`/ns/${namespace}/configs/${item.path}`)
      }
      showToast(wasNew ? 'Config created' : 'Config saved')
      setIsDirty(false)
    },
    onError: (e: Error) => pushApiError('Save failed', e),
  })

  const canSave = canEdit
    && !resolveMounted
    && (item.version === 0 || isDirty)
    && hasEditorContent(content)
    && isHealthy()

  const saveShortcut = useItemSaveShortcut({
    canSave,
    onSave: () => saveMut.mutate(),
  })
  saveShortcutMountRef.current = saveShortcut.onEditorMount

  const propagateMut = useMutation({
    mutationFn: () => treeApi.propagate(namespace, item.path),
    onSuccess: (result: PropagationResult) => {
      setPropagateOpen(false)
      const targets = result.targets ?? []
      const updated = targets.filter(t => t.status === 'updated').length
      const errors = targets.filter(t => t.status === 'error')

      if (errors.length > 0) {
        pushNotification(
          'warning',
          `Propagation completed with ${errors.length} error(s)`,
          errors.map(t => `${t.path}: ${t.reason ?? 'failed'}`).join('\n'),
        )
      } else if (updated > 0) {
        showToast(`Propagated to ${updated} target(s)`)
      } else {
        showToast('Propagation finished; no targets updated')
      }
    },
    onError: (e: Error) => pushApiError('Propagation failed', e),
  })

  const tabs: Array<{ id: Tab; label: string; icon: React.ReactNode }> = creating
    ? [{ id: 'editor', label: 'Editor', icon: null }]
    : [
        { id: 'editor', label: 'Editor', icon: null },
        { id: 'history', label: 'History', icon: <History className="h-3.5 w-3.5" /> },
        ...(permissions.canAudit
          ? [{ id: 'audit' as const, label: 'Audit', icon: <ScrollText className="h-3.5 w-3.5" /> }]
          : []),
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

  const resetContent = useCallback(() => {
    setContent(item.content ?? '')
    setIsDirty(false)
  }, [item.content])

  const openResolve = useCallback(() => {
    setResolveMounted(true)
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setResolveOpen(true))
    })
  }, [])

  const closeResolve = useCallback(() => {
    setResolveOpen(false)
  }, [])

  const handleResolveTransitionEnd = useCallback((e: React.TransitionEvent<HTMLDivElement>) => {
    if (e.target !== e.currentTarget || e.propertyName !== 'transform') return
    if (!resolveOpen) setResolveMounted(false)
  }, [resolveOpen])

  useEffect(() => {
    if (activeTab !== 'editor' && resolveMounted) {
      closeResolve()
    }
  }, [activeTab, resolveMounted, closeResolve])

  useEffect(() => {
    if (isJsonSchemaMode && resolveMounted) {
      closeResolve()
    }
  }, [isJsonSchemaMode, resolveMounted, closeResolve])

  return (
    <div className="flex h-full flex-col">
      {!creating && (
        <>
          <ItemHeader
            namespace={namespace}
            path={item.path}
            type="config"
            version={item.version}
            tags={item.tags}
            showVersionSelector
            deletedAt={item.deleted_at}
            onDelete={canDeleteItem && !isDeleted ? () => setDeleteOpen(true) : undefined}
            onMove={canMoveItem && !isDeleted ? () => setMoveOpen(true) : undefined}
            onCopy={canCopyItem && !isDeleted ? () => setCopyOpen(true) : undefined}
            onPropagate={showPropagate && permissions.canRead ? () => setPropagateOpen(true) : undefined}
          />

          <ItemDescription
            namespace={namespace}
            path={item.path}
            description={item.description}
            canEdit={permissions.canDescribe}
          />
        </>
      )}

      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className={cn(
          'flex items-center gap-0.5 border-b px-4 dark:border-gray-700',
          creating && 'py-2',
        )}>
          {!creating && tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={cn(
                'flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors',
                activeTab === t.id
                  ? 'border-brand-500 text-brand-700 dark:text-brand-300'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400',
              )}
            >
              {t.icon}
              {t.label}
            </button>
          ))}

          <div className="flex-1" />

          {isDirty && activeTab === 'editor' && !isDeleted && (
            <span className="mr-2 flex items-center gap-1.5 text-xs text-yellow-600 dark:text-yellow-400">
              <AlertTriangle className="h-3 w-3" />
              Unsaved changes
              {canEdit && (
                <button
                  type="button"
                  onClick={resetContent}
                  className="rounded p-0.5 text-yellow-700/80 hover:bg-yellow-100 hover:text-yellow-900 dark:text-yellow-300/80 dark:hover:bg-yellow-900/30 dark:hover:text-yellow-200"
                  title="Discard changes"
                  aria-label="Reset to saved content"
                >
                  <RotateCcw className="h-3 w-3" />
                </button>
              )}
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
          ) : activeTab === 'audit' ? null : !isDeleted ? (
            <>
              {canEdit && !resolveMounted && (
                <ItemSaveButton
                  label={creating ? 'Create' : 'Save'}
                  loading={saveMut.isPending}
                  disabled={!canSave}
                  onClick={() => saveMut.mutate()}
                  buttonRef={saveShortcut.buttonRef}
                  showEnterHint={saveShortcut.showEnterHint}
                  enterHint={saveShortcut.enterHint}
                  onKeyDown={saveShortcut.handleButtonKeyDown}
                  className="mr-2"
                />
              )}
              {canResolve && !resolveMounted && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={openResolve}
                  className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
                >
                  Resolve
                  <ChevronLeft className="h-3.5 w-3.5" />
                </Button>
              )}
            </>
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
              language="yaml"
              theme={monacoTheme}
              path={editorModelPath}
              value={content}
              onMount={handleEditorMount}
              onChange={v => {
                if (!canEdit) return
                setContent(v ?? '')
                setIsDirty(true)
              }}
              options={yamlEditorOptions(!canEdit)}
            />
          )}
          {activeTab === 'history' && (
            <ItemHistoryTab
              namespace={namespace}
              path={item.path}
              itemType="config"
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
            <ItemAuditTab namespace={namespace} path={item.path} type="config" />
          )}
        </div>

        {(creating || activeTab === 'editor') && !isDeleted && resolveMounted && canResolve && (
          <div
            className={cn(
              'absolute inset-0 z-10 transition-transform duration-300 ease-in-out',
              resolveOpen ? 'translate-x-0' : 'translate-x-full',
            )}
            onTransitionEnd={handleResolveTransitionEnd}
          >
            <ResolvePanel
              namespace={namespace}
              path={item.path}
              versionRef={versionRef}
              content={content}
              isDirty={useDraftResolve}
              onClose={closeResolve}
            />
          </div>
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
        type="config"
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
      />

      <LocationDialog
        mode="copy"
        namespace={namespace}
        path={item.path}
        type="config"
        tags={item.tags}
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
      />

      <Modal
        open={propagateOpen}
        onClose={() => setPropagateOpen(false)}
        title="Manual propagation"
        footer={
          <>
            <Button variant="ghost" onClick={() => setPropagateOpen(false)}>Cancel</Button>
            <Button variant="primary" loading={propagateMut.isPending} onClick={() => propagateMut.mutate()}>
              <Route className="h-3.5 w-3.5" />
              Propagate
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Manually trigger change propagation for <strong className="font-mono">{item.path}</strong>.
        </p>
      </Modal>
    </div>
  )
}
