import { useCallback, useEffect, useRef, useState } from 'react'
import { formatUserDateTime, formatUserDateTimeRelative } from '../../lib/datetime'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import MonacoEditor from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import { RotateCcw, Copy, AlertTriangle, Eye, EyeOff } from 'lucide-react'
import { treeApi } from '../../api/tree'
import type { ResolverCreateResponse, ResolverNode } from '../../api/types'
import type { useItemPermissions } from '../../hooks/useItemPermissions'
import { useResolverYamlSchema } from '../../hooks/useResolverYamlSchema'
import { useItemSaveShortcut } from '../../hooks/useItemSaveShortcut'
import { registerYamlSchemaCompletion, installYamlCompletionTriggers } from '../../lib/yamlCompletion'
import { installYamlEditorEmptyHint } from '../../lib/yamlEditorEmptyHint'
import { useMonacoEditorTheme } from '../../hooks/useMonacoEditorTheme'
import { yamlEditorOptions } from '../../lib/yamlEditorOptions'
import { ItemHeader } from './ItemHeader'
import { DeleteDialog } from './DeleteDialog'
import { LocationDialog } from './LocationDialog'
import { ItemDescription } from './ItemDescription'
import { ItemAuditTab } from './ItemAuditTab'
import { PermissionDenied } from './PermissionDenied'
import { ItemSaveButton } from './ItemSaveButton'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import { pushApiError } from '../../store/notifications'
import { showToast } from '../ui/Toast'
import { isHealthy } from '../../store/health'
import { invalidateItemDetailQueries, invalidateTreeQueries } from '../../lib/treeQuery'
import { createItemEditorModelPath } from '../../lib/configEditorSchema'
import { cn } from '../ui/cn'
import type { ItemEditorMode } from '../../lib/itemEditorMode'
import { isCreateMode } from '../../lib/itemEditorMode'

type Tab = 'config' | 'tokens' | 'audit'

const TAB_LABELS: Record<Tab, string> = {
  config: 'Resolver config',
  tokens: 'Tokens',
  audit: 'Audit',
}

function formatTokenLastUsed(lastUsed: string | null): string {
  if (!lastUsed) return 'never'
  const relative = formatUserDateTimeRelative(lastUsed)
  return relative === '—' ? 'never' : relative
}

function resolverEditorModelPath(namespace: string, path: string): string {
  return `resolver-editor/${namespace}/${path}.yaml`
}

type ResolverNavigationState = {
  createdToken?: string
}

export default function ResolverView({
  item,
  namespace,
  permissions,
  mode = 'edit',
}: {
  item: ResolverNode
  namespace: string
  permissions: ReturnType<typeof useItemPermissions>
  mode?: ItemEditorMode
}) {
  const creating = isCreateMode(mode)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()
  const navState = location.state as ResolverNavigationState | null
  const createdTokenFromNavigation = navState?.createdToken
  const [activeTab, setActiveTab] = useState<Tab>(() => (createdTokenFromNavigation ? 'tokens' : 'config'))
  const [content, setContent] = useState(() => {
    if (!item.configuration) return ''
    return typeof item.configuration === 'string'
      ? item.configuration
      : JSON.stringify(item.configuration, null, 2)
  })
  const [isDirty, setIsDirty] = useState(false)
  const [rotateConfirm, setRotateConfirm] = useState<1 | 2 | null>(null)
  const [newToken, setNewToken] = useState<string | null>(() => createdTokenFromNavigation ?? null)
  const [isInitialToken, setIsInitialToken] = useState(() => Boolean(createdTokenFromNavigation))
  const [tokenVisible, setTokenVisible] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [moveOpen, setMoveOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const monacoTheme = useMonacoEditorTheme()

  useEffect(() => {
    if (!createdTokenFromNavigation) return
    setNewToken(createdTokenFromNavigation)
    setIsInitialToken(true)
    setActiveTab('tokens')
    navigate(`${location.pathname}${location.search}`, { replace: true, state: null })
  }, [createdTokenFromNavigation, location.pathname, location.search, navigate])

  const { schema, isReady } = useResolverYamlSchema()
  const modelPath = creating
    ? createItemEditorModelPath(namespace, 'resolver')
    : resolverEditorModelPath(namespace, item.path)
  const monacoRef = useRef<typeof import('monaco-editor') | null>(null)
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const schemaRef = useRef(schema)
  schemaRef.current = schema
  const completionDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const suggestTriggerDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const emptyHintDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const saveShortcutMountRef = useRef<
    (editorInstance: editor.IStandaloneCodeEditor, monaco: typeof import('monaco-editor')) => void
  >(() => {})

  const attachSchemaCompletion = useCallback((monaco: typeof import('monaco-editor')) => {
    completionDisposableRef.current?.dispose()
    if (!schemaRef.current) return
    completionDisposableRef.current = registerYamlSchemaCompletion(
      monaco,
      () => schemaRef.current,
      editorRef.current ?? undefined,
    )
  }, [])

  const attachSuggestTriggers = useCallback((
    editorInstance: editor.IStandaloneCodeEditor,
    monaco: typeof import('monaco-editor'),
  ) => {
    suggestTriggerDisposableRef.current?.dispose()
    suggestTriggerDisposableRef.current = installYamlCompletionTriggers(
      editorInstance,
      monaco,
      () => schemaRef.current,
    )
  }, [])

  const handleEditorMount = (
    editorInstance: editor.IStandaloneCodeEditor,
    monaco: typeof import('monaco-editor'),
  ) => {
    monacoRef.current = monaco
    editorRef.current = editorInstance
    attachSchemaCompletion(monaco)
    attachSuggestTriggers(editorInstance, monaco)
    emptyHintDisposableRef.current?.dispose()
    emptyHintDisposableRef.current = installYamlEditorEmptyHint(editorInstance, monaco, {
      hasSuggestions: () => !!schemaRef.current,
    })
    saveShortcutMountRef.current(editorInstance, monaco)
  }

  useEffect(() => {
    if (monacoRef.current) {
      attachSchemaCompletion(monacoRef.current)
    }
    emptyHintDisposableRef.current?.refresh()
  }, [attachSchemaCompletion, schema])

  useEffect(() => () => {
    completionDisposableRef.current?.dispose()
    suggestTriggerDisposableRef.current?.dispose()
    emptyHintDisposableRef.current?.dispose()
  }, [])

  const saveMut = useMutation({
    mutationFn: async (): Promise<ResolverCreateResponse | void> => {
      if (item.version === 0) {
        return treeApi.createResolver(namespace, item.path, content)
      }
      await treeApi.updateResolver(namespace, item.path, content)
    },
    onSuccess: (data) => {
      const wasNew = item.version === 0
      invalidateItemDetailQueries(qc, namespace, item.path)
      invalidateTreeQueries(qc, namespace, item.path)
      if (wasNew) {
        navigate(`/ns/${namespace}/configs/${item.path}`, {
          replace: true,
          state: data?.token1 ? { createdToken: data.token1 } : null,
        })
      }
      showToast(wasNew ? 'Resolver created' : 'Resolver saved')
      setIsDirty(false)
    },
    onError: (e: Error) => pushApiError('Save failed', e),
  })

  const canSave = permissions.canWrite
    && (item.version === 0 || isDirty)
    && isHealthy()

  const saveShortcut = useItemSaveShortcut({
    canSave,
    onSave: () => saveMut.mutate(),
  })
  saveShortcutMountRef.current = saveShortcut.onEditorMount

  const canDeleteItem = permissions.canDelete
  const canMoveItem = permissions.canMove
  const canCopyItem = permissions.canCopy

  const rotateMut = useMutation({
    mutationFn: (tokenNumber: 1 | 2) => treeApi.rotateToken(namespace, item.path, { token_number: tokenNumber }),
    onSuccess: (data) => {
      invalidateItemDetailQueries(qc, namespace, item.path)
      setNewToken(data.token)
      setIsInitialToken(false)
      setTokenVisible(false)
      setRotateConfirm(null)
    },
    onError: (e: Error) => pushApiError('Token rotation failed', e),
  })

  return (
    <div className="flex h-full flex-col">
      {!creating && (
        <>
          <ItemHeader
            namespace={namespace}
            path={item.path}
            type="resolver"
            version={item.version}
            onDelete={canDeleteItem ? () => setDeleteOpen(true) : undefined}
            onMove={canMoveItem ? () => setMoveOpen(true) : undefined}
            onCopy={canCopyItem ? () => setCopyOpen(true) : undefined}
          />
          <ItemDescription
            namespace={namespace}
            path={item.path}
            description={item.description}
            canEdit={permissions.canDescribe}
          />
        </>
      )}
      {!creating ? (
        <div className="flex items-center gap-0.5 border-b px-4 dark:border-gray-700">
          {(['config', 'tokens', ...(permissions.canAudit ? ['audit' as const] : [])] as Tab[]).map(t => (
            <button key={t} onClick={() => setActiveTab(t)}
              className={cn('border-b-2 px-3 py-2 text-xs font-medium',
                activeTab === t ? 'border-brand-500 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-700')}
            >{TAB_LABELS[t]}</button>
          ))}
          <div className="flex-1" />
          {activeTab === 'config' && isDirty && (
            <span className="flex items-center gap-1 text-xs text-yellow-600 mr-2">
              <AlertTriangle className="h-3 w-3" /> Unsaved
            </span>
          )}
          {activeTab === 'config' && permissions.canWrite && (
            <ItemSaveButton
              label="Save"
              loading={saveMut.isPending}
              disabled={!canSave}
              onClick={() => saveMut.mutate()}
              buttonRef={saveShortcut.buttonRef}
              showEnterHint={saveShortcut.showEnterHint}
              enterHint={saveShortcut.enterHint}
              onKeyDown={saveShortcut.handleButtonKeyDown}
            />
          )}
        </div>
      ) : (
        <div className="flex items-center justify-end gap-2 border-b px-4 py-2 dark:border-gray-700">
          {isDirty && (
            <span className="flex items-center gap-1 text-xs text-yellow-600">
              <AlertTriangle className="h-3 w-3" /> Unsaved
            </span>
          )}
          {permissions.canWrite && (
            <ItemSaveButton
              label="Create"
              loading={saveMut.isPending}
              disabled={!canSave}
              onClick={() => saveMut.mutate()}
              buttonRef={saveShortcut.buttonRef}
              showEnterHint={saveShortcut.showEnterHint}
              enterHint={saveShortcut.enterHint}
              onKeyDown={saveShortcut.handleButtonKeyDown}
            />
          )}
        </div>
      )}
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        {creating && !permissions.canWrite && (
          <PermissionDenied message="You do not have permission to create resolvers." />
        )}
        {(creating || activeTab === 'config') && !creating && !permissions.canRead && (
          <PermissionDenied message="You do not have permission to view this resolver configuration." />
        )}
        {(creating || activeTab === 'config') && (creating ? permissions.canWrite : permissions.canRead) && (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <MonacoEditor
            height="100%"
            language="yaml"
            theme={monacoTheme}
            path={modelPath}
            value={content}
            onMount={handleEditorMount}
            onChange={v => { setContent(v ?? ''); setIsDirty(true) }}
            options={yamlEditorOptions(!permissions.canWrite)}
            loading={!isReady ? 'Loading schema…' : undefined}
          />
          </div>
        )}
        {activeTab === 'tokens' && permissions.canRead && (
          <div className="p-6 space-y-6">
            {(item.author || item.created_at) && (
              <p className="text-xs text-gray-500">
                Created by {item.author || '—'} · {formatUserDateTime(item.created_at)}
              </p>
            )}
            <div className="rounded-lg border border-slate-300 p-4 dark:border-gray-700 space-y-4">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Resolver tokens</p>
              <p className="text-xs text-gray-500">
                Tokens are only shown in full immediately after creation or rotation.
                Use two tokens for zero-downtime rotation.
              </p>
              {([1, 2] as const).map(n => (
                <div key={n} className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-12">Token {n}</span>
                    <code className="flex-1 rounded bg-slate-200 px-2 py-1 text-xs font-mono dark:bg-gray-800">
                      {(n === 1 ? item.token1 : item.token2) ?? '—'}
                    </code>
                    {permissions.canWrite && (
                      <Button variant="ghost" size="sm" onClick={() => setRotateConfirm(n)}>
                        <RotateCcw className="h-3.5 w-3.5" /> Rotate
                      </Button>
                    )}
                  </div>
                  <p className="pl-[3.75rem] text-xs text-gray-500">
                    Last used: {formatTokenLastUsed(n === 1 ? item.token1_last_used : item.token2_last_used)}
                  </p>
                </div>
              ))}
            </div>

            {newToken && permissions.canWrite && (
              <div className="rounded-lg border-2 border-green-400 bg-green-50 p-4 dark:border-green-700 dark:bg-green-900/10">
                <p className="text-sm font-semibold text-green-800 dark:text-green-300">
                  {isInitialToken ? 'Initial resolver token' : 'New token'} (shown once only — copy and store securely)
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 rounded bg-surface-elevated px-2 py-1 text-xs font-mono text-green-900 dark:bg-gray-800 dark:text-green-300">
                    {tokenVisible ? newToken : '•'.repeat(newToken.length)}
                  </code>
                  <Button variant="ghost" size="sm" title={tokenVisible ? 'Hide token' : 'Show token'} onClick={() => setTokenVisible(v => !v)}>
                    {tokenVisible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => {
                    void navigator.clipboard.writeText(newToken)
                    showToast('Token copied to clipboard')
                  }}>
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => {
                    setNewToken(null)
                    setIsInitialToken(false)
                    setTokenVisible(false)
                  }}>
                    Dismiss
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
        {activeTab === 'tokens' && !permissions.canRead && (
          <PermissionDenied message="You do not have permission to view resolver tokens." />
        )}
        {activeTab === 'audit' && (
          <ItemAuditTab namespace={namespace} path={item.path} type="resolver" />
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
        type="resolver"
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
      />

      <LocationDialog
        mode="copy"
        namespace={namespace}
        path={item.path}
        type="resolver"
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
      />

      <Modal open={!!rotateConfirm} onClose={() => setRotateConfirm(null)} title={`Rotate token ${rotateConfirm}`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setRotateConfirm(null)}>Cancel</Button>
            <Button variant="danger" loading={rotateMut.isPending}
              onClick={() => rotateConfirm && rotateMut.mutate(rotateConfirm)}>
              Rotate
            </Button>
          </>
        }
      >
        <p className="text-sm text-gray-600 dark:text-gray-400">
          A new token will be generated. The previous token {rotateConfirm} will be invalidated.
          The new token will be shown once — copy it before navigating away.
        </p>
      </Modal>
    </div>
  )
}
