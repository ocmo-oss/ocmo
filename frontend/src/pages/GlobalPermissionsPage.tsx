import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import MonacoEditor from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import { Plus, Trash2, ArrowUp, ArrowDown, Edit } from 'lucide-react'
import { permissionsApi } from '../api/permissions'
import type { GlobalPermissionRule, GlobalPermissionRulePayload } from '../api/types'
import { Button } from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { Skeleton } from '../components/ui/Skeleton'
import { pushApiError } from '../store/notifications'
import { showToast } from '../components/ui/Toast'
import { useMonacoEditorTheme } from '../hooks/useMonacoEditorTheme'
import { useAuth } from '../auth/useAuth'
import { registerYamlSchemaCompletion, installYamlCompletionTriggers } from '../lib/yamlCompletion'
import { installYamlEditorEmptyHint } from '../lib/yamlEditorEmptyHint'
import { yamlEditorOptions } from '../lib/yamlEditorOptions'
import { buildGlobalPermissionRuleSchema } from '../lib/globalPermissionRuleSchema'
import { QueryAccessGate } from '../components/QueryAccessGate'
import {
  NEW_GLOBAL_PERMISSION_RULE_TEMPLATE,
  parseRulePayloadYaml,
  rulePayloadToYaml,
} from '../lib/globalPermissionYaml'

const RULE_EDITOR_MODEL_PATH = 'global-permission-rule-editor/rule.yaml'

function RuleEditorModal({
  rule,
  open,
  onClose,
}: {
  rule: GlobalPermissionRule | null
  open: boolean
  onClose: () => void
}) {
  const qc = useQueryClient()
  const { whoami } = useAuth()
  const isNew = rule === null
  const monacoTheme = useMonacoEditorTheme()
  const [yaml, setYaml] = useState(() =>
    isNew ? NEW_GLOBAL_PERMISSION_RULE_TEMPLATE : rulePayloadToYaml(rule.rule),
  )

  const userClaims = whoami?.auth_type === 'user' ? whoami.user_details.claims : undefined
  const composedSchema = useMemo(
    () => buildGlobalPermissionRuleSchema(userClaims),
    [userClaims],
  )

  const monacoRef = useRef<typeof import('monaco-editor') | null>(null)
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const composedSchemaRef = useRef(composedSchema)
  composedSchemaRef.current = composedSchema
  const completionDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const suggestTriggerDisposableRef = useRef<import('monaco-editor').IDisposable | null>(null)
  const emptyHintDisposableRef = useRef<(import('monaco-editor').IDisposable & { refresh: () => void }) | null>(null)

  const attachSchemaCompletion = useCallback((monaco: typeof import('monaco-editor')) => {
    completionDisposableRef.current?.dispose()
    completionDisposableRef.current = registerYamlSchemaCompletion(
      monaco,
      () => composedSchemaRef.current,
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
      () => composedSchemaRef.current,
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
      hasSuggestions: () => true,
    })
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

  const mut = useMutation({
    mutationFn: () => {
      let payload: GlobalPermissionRulePayload
      try {
        payload = parseRulePayloadYaml(yaml)
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Invalid YAML'
        throw new Error(message)
      }
      return isNew
        ? permissionsApi.create(payload)
        : permissionsApi.update(rule!.id, payload)
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['global-permissions'] })
      showToast(isNew ? 'Rule created' : 'Rule updated')
      onClose()
    },
    onError: (e: Error) => pushApiError('Failed to save rule', e),
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isNew ? 'Add permission rule' : 'Edit permission rule'}
      size="xl"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={mut.isPending} onClick={() => mut.mutate()}>
            {isNew ? 'Create' : 'Save'}
          </Button>
        </>
      }
    >
      <div className="h-72">
        <MonacoEditor
          height="100%"
          path={RULE_EDITOR_MODEL_PATH}
          language="yaml"
          theme={monacoTheme}
          value={yaml}
          onChange={v => setYaml(v ?? '')}
          onMount={handleEditorMount}
          options={yamlEditorOptions()}
        />
      </div>
    </Modal>
  )
}

export function GlobalPermissionsPage() {
  const qc = useQueryClient()
  const [editRule, setEditRule] = useState<GlobalPermissionRule | null>(null)
  const [editorOpen, setEditorOpen] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['global-permissions'],
    queryFn: ({ signal }) => permissionsApi.list({ limit: 100 }, signal),
    staleTime: 30_000,
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => permissionsApi.delete(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['global-permissions'] })
      showToast('Rule deleted')
    },
    onError: (e: Error) => pushApiError('Delete failed', e),
  })

  const moveMut = useMutation({
    mutationFn: ({ id, pos }: { id: string; pos: number }) => permissionsApi.move(id, { position: pos }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['global-permissions'] }),
  })

  const openNew = () => {
    setEditRule(null)
    setEditorOpen(true)
  }

  const openEdit = (rule: GlobalPermissionRule) => {
    setEditRule(rule)
    setEditorOpen(true)
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">Global Permissions</h1>
        </div>
        <Button variant="primary" size="sm" onClick={openNew}>
          <Plus className="h-4 w-4" /> Add rule
        </Button>
      </div>

      <div className="mb-6 rounded-lg border border-slate-300 bg-surface px-4 py-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800/40 dark:text-gray-400">
        <p>
          Global permissions control which OIDC users may access which namespaces. Each rule matches a
          namespace name or glob pattern (for example <span className="font-mono">prod</span> or{' '}
          <span className="font-mono">team-*</span>) and grants one or more gates to matching users.
          Rules are evaluated top to bottom; the first match wins. Access is denied by default.
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
          <li>
            <strong className="font-medium text-gray-700 dark:text-gray-300">read</strong> — see the
            namespace in listings, open it, and browse items. Actions on individual items still depend on
            that namespace&apos;s <span className="font-mono">_permissions</span> policy.
          </li>
          <li>
            <strong className="font-medium text-gray-700 dark:text-gray-300">write</strong> — everything
            read allows, plus edit namespace settings and the namespace{' '}
            <span className="font-mono">_permissions</span> policy.
          </li>
          <li>
            <strong className="font-medium text-gray-700 dark:text-gray-300">delete</strong> — delete the
            namespace and all of its contents.
          </li>
          <li>
            <strong className="font-medium text-gray-700 dark:text-gray-300">audit</strong> — view the audit
            log for the namespace.
          </li>
        </ul>
        <p className="mt-2 text-xs">
          Global administrators always have <span className="font-mono">read</span> and{' '}
          <span className="font-mono">audit</span> on every namespace without a matching rule.{' '}
          <span className="font-mono">write</span> and <span className="font-mono">delete</span> still
          require an explicit rule, even for global administrators. Only global administrators can edit
          these rules.
        </p>
      </div>

      <QueryAccessGate
        isLoading={isLoading}
        isError={isError}
        error={error}
        hasData={!!data}
        permissionDeniedMessage="You do not have permission to manage global permissions."
        loadingFallback={<Skeleton lines={5} className="h-16 w-full" />}
      >
      {!isLoading && (data?.rules.length ?? 0) === 0 && (
        <div className="rounded-lg border border-dashed p-12 text-center dark:border-gray-700">
          <p className="text-sm text-gray-400">No rules defined — all access is denied by default.</p>
        </div>
      )}

      <div className="space-y-2">
        {data?.rules.map((rule, idx) => (
          <div
            key={rule.id}
            className="flex items-center gap-3 rounded-lg border px-4 py-3 dark:border-gray-700 bg-surface-elevated dark:bg-gray-900"
          >
            <span className="w-6 text-xs text-gray-400 font-mono">{idx + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="font-mono text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                Namespace(s): {rule.rule.namespace}
              </div>
              <div className="mt-0.5 font-mono text-xs text-gray-400 truncate">
                {rule.rule.id ?? rule.id}
              </div>
              {rule.rule.description && (
                <p className="text-xs text-gray-500 mt-0.5 truncate">{rule.rule.description}</p>
              )}
              <div className="flex gap-1 mt-1">
                {rule.rule.read && <span className="text-xs bg-blue-50 text-blue-700 px-1.5 rounded dark:bg-blue-900/20 dark:text-blue-300">read</span>}
                {rule.rule.write && <span className="text-xs bg-green-50 text-green-700 px-1.5 rounded dark:bg-green-900/20 dark:text-green-300">write</span>}
                {rule.rule.delete && <span className="text-xs bg-red-50 text-red-700 px-1.5 rounded dark:bg-red-900/20 dark:text-red-300">delete</span>}
                {rule.rule.audit && <span className="text-xs bg-slate-200 text-gray-600 px-1.5 rounded dark:bg-gray-800">audit</span>}
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" disabled={idx === 0} onClick={() => moveMut.mutate({ id: rule.id, pos: rule.position - 1 })}>
                <ArrowUp className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" disabled={idx === (data?.rules.length ?? 0) - 1} onClick={() => moveMut.mutate({ id: rule.id, pos: rule.position + 1 })}>
                <ArrowDown className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => openEdit(rule)}>
                <Edit className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" loading={deleteMut.isPending} onClick={() => deleteMut.mutate(rule.id)}>
                <Trash2 className="h-3.5 w-3.5 text-red-500" />
              </Button>
            </div>
          </div>
        ))}
      </div>
      </QueryAccessGate>

      <RuleEditorModal
        key={editRule?.id ?? 'new'}
        rule={editRule}
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
      />
    </div>
  )
}
