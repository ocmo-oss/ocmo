import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import MonacoEditor from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { EyeOff, History, AlertTriangle, ScrollText } from "lucide-react";
import { treeApi } from "../../api/tree";
import type { SecretNode } from "../../api/types";
import type { useItemPermissions } from "../../hooks/useItemPermissions";
import { useItemVersion } from "../../hooks/useItemVersion";
import { useHistorySelection } from "../../hooks/useHistorySelection";
import { useItemSaveShortcut } from "../../hooks/useItemSaveShortcut";
import { ItemHeader } from "./ItemHeader";
import { ItemDescription } from "./ItemDescription";
import { ItemHistoryTab } from "./ItemHistoryTab";
import { ItemAuditTab } from "./ItemAuditTab";
import { HistoryTabActions } from "./HistoryTabActions";
import { PermissionDenied } from "./PermissionDenied";
import { DeletedVersionNotice } from "./DeletedVersionNotice";
import { DeleteDialog } from "./DeleteDialog";
import { LocationDialog } from "./LocationDialog";
import { ItemSaveButton } from "./ItemSaveButton";
import { pushApiError } from "../../store/notifications";
import { showToast } from "../ui/Toast";
import { isHealthy } from "../../store/health";
import {
  invalidateItemDetailQueries,
  invalidateTreeQueries,
} from "../../lib/treeQuery";
import { useMonacoEditorTheme } from "../../hooks/useMonacoEditorTheme";
import { yamlEditorOptions } from "../../lib/yamlEditorOptions";
import { installEditorEmptyHint } from "../../lib/editorEmptyHint";
import { isBuiltinNamespacePath } from "../../lib/builtinPaths";
import { cn } from "../ui/cn";
import type { ItemEditorMode } from "../../lib/itemEditorMode";
import { isCreateMode, hasEditorContent } from "../../lib/itemEditorMode";

type Tab = "editor" | "history" | "audit";

const SECRET_EDITOR_PLACEHOLDER = "Type YAML structured or raw sensitive data";

const DUMMY_SECRET_VARIANTS = [
  `database:
  host: db.example.internal
  port: 5432
  username: app_service
  password: xxxxxxxxxxxxxxxxxxxxxxxx

api:
  key: xxxxxxxxxxxxxxxxxxxxxxxx
  secret: xxxxxxxxxxxxxxxxxxxxxxxx
`,
  `oauth:
  client_id: xxxxxxxxxxxxxxxxxxxxxxxx
  client_secret: xxxxxxxxxxxxxxxxxxxxxxxx
  token_url: https://auth.example.com/oauth/token

refresh_token: xxxxxxxxxxxxxxxxxxxxxxxx
`,
  `ssh:
  private_key: |
    -----BEGIN ENCRYPTED PRIVATE KEY-----
    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    -----END ENCRYPTED PRIVATE KEY-----
  passphrase: xxxxxxxxxxxxxxxxxxxxxxxx
`,
  `webhook:
  signing_secret: xxxxxxxxxxxxxxxxxxxxxxxx
  hmac_key: xxxxxxxxxxxxxxxxxxxxxxxx

endpoints:
  - https://hooks.example.com/inbound/a1b2c3
  - https://hooks.example.com/inbound/d4e5f6
`,
] as const;

function pickDummySecretContent(): string {
  const index = Math.floor(Math.random() * DUMMY_SECRET_VARIANTS.length);
  return DUMMY_SECRET_VARIANTS[index] ?? DUMMY_SECRET_VARIANTS[0];
}

function selectionToDiffRef(item: {
  kind: string;
  tagName?: string;
  version: number;
}) {
  if (item.kind === "tag" && item.tagName) return item.tagName;
  return String(item.version);
}

type SecretNavigationState = {
  revealSecret?: boolean;
  secretContent?: string;
};

export default function SecretView({
  item,
  namespace,
  permissions,
  mode = "edit",
}: {
  item: SecretNode;
  namespace: string;
  permissions: ReturnType<typeof useItemPermissions>;
  mode?: ItemEditorMode;
}) {
  const creating = isCreateMode(mode);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const { versionRef } = useItemVersion();
  const isNew = item.version === 0;
  const navState = location.state as SecretNavigationState | null;
  const revealFromNavigation = navState?.revealSecret === true;
  const prevPathRef = useRef(item.path);
  const prevVersionRefRef = useRef(versionRef);
  const emptyHintDisposableRef = useRef<
    import("monaco-editor").IDisposable | null
  >(null);
  const saveShortcutMountRef = useRef<
    (
      editorInstance: editor.IStandaloneCodeEditor,
      monaco: typeof import("monaco-editor"),
    ) => void
  >(() => {});
  const monacoTheme = useMonacoEditorTheme();
  const [activeTab, setActiveTab] = useState<Tab>("editor");
  const [placeholderContent, setPlaceholderContent] = useState(
    pickDummySecretContent,
  );
  const [content, setContent] = useState(() => {
    if (isNew) return "";
    if (revealFromNavigation) return navState?.secretContent ?? "";
    return "";
  });
  const [savedContent, setSavedContent] = useState(() =>
    revealFromNavigation ? (navState?.secretContent ?? "") : "",
  );
  const [isDirty, setIsDirty] = useState(false);
  const [revealed, setRevealed] = useState(() => isNew || revealFromNavigation);
  const [contentHydrated, setContentHydrated] = useState(
    () => isNew || revealFromNavigation,
  );
  const [diffPair, setDiffPair] = useState<{ from: string; to: string } | null>(
    null,
  );
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [moveOpen, setMoveOpen] = useState(false);
  const [copyOpen, setCopyOpen] = useState(false);
  const {
    selected: historySelected,
    toggle: toggleHistory,
    isSelected: isHistorySelected,
    clear: clearHistorySelection,
    canDiff,
    canUntag,
    canRemove,
  } = useHistorySelection();

  const canEdit = permissions.canWrite;
  const canDeleteItem =
    permissions.canDelete && !isBuiltinNamespacePath(item.path);
  const canMoveItem = permissions.canMove && !isBuiltinNamespacePath(item.path);
  const canCopyItem = permissions.canCopy && !isBuiltinNamespacePath(item.path);

  useEffect(() => {
    if (!revealFromNavigation) return;
    navigate(`${location.pathname}${location.search}`, {
      replace: true,
      state: null,
    });
  }, [revealFromNavigation, location.pathname, location.search, navigate]);

  useEffect(() => {
    const pathChanged = prevPathRef.current !== item.path;
    const versionRefChanged = prevVersionRefRef.current !== versionRef;

    if (!pathChanged && !versionRefChanged) return;

    prevPathRef.current = item.path;
    prevVersionRefRef.current = versionRef;

    prevPathRef.current = item.path;
    prevVersionRefRef.current = versionRef;

    if (pathChanged && creating) {
      return;
    }

    if (pathChanged) {
      setPlaceholderContent(pickDummySecretContent());
      setIsDirty(false);

      if (isNew) {
        setContent("");
        setSavedContent("");
        setRevealed(true);
        setContentHydrated(true);
      } else {
        setContent("");
        setSavedContent("");
        setRevealed(false);
        setContentHydrated(false);
      }
      return;
    }

    setPlaceholderContent(pickDummySecretContent());
    setContent("");
    setSavedContent("");
    setIsDirty(false);
    setRevealed(false);
    setContentHydrated(false);
  }, [item.path, versionRef, isNew, creating]);

  useEffect(() => {
    if (activeTab !== "history") {
      clearHistorySelection();
      setDiffPair(null);
    }
  }, [activeTab, clearHistorySelection]);

  useEffect(
    () => () => {
      emptyHintDisposableRef.current?.dispose();
    },
    [],
  );

  const handleSecretEditorMount = (
    editorInstance: editor.IStandaloneCodeEditor,
    monaco: typeof import("monaco-editor"),
  ) => {
    emptyHintDisposableRef.current?.dispose();
    emptyHintDisposableRef.current = installEditorEmptyHint(
      editorInstance,
      monaco,
      {
        text: SECRET_EDITOR_PLACEHOLDER,
      },
    );
    saveShortcutMountRef.current(editorInstance, monaco);
  };

  const handleDiffWithCurrent = (otherRef: string) => {
    const current = versionRef ?? "latest";
    setDiffPair({ from: otherRef, to: current });
  };

  const handleDiff = () => {
    if (historySelected.length !== 2) return;
    const [a, b] = historySelected;
    setDiffPair({
      from: selectionToDiffRef(a),
      to: selectionToDiffRef(b),
    });
  };

  const {
    data: revealedItem,
    isFetching: revealing,
    error: revealError,
    refetch: refetchReveal,
  } = useQuery({
    queryKey: ["item-reveal", namespace, item.path, item.version],
    queryFn: ({ signal }) =>
      treeApi.get(
        namespace,
        item.path,
        { reveal: true, version: String(item.version) },
        signal,
      ),
    enabled: revealed && !isNew && permissions.canRead,
    staleTime: 0,
    gcTime: 0,
  });

  const revealedContent =
    revealed && revealedItem?.type === "secret"
      ? revealedItem.content
      : undefined;

  useEffect(() => {
    if (revealedContent === undefined) return;
    setContent(revealedContent);
    setSavedContent(revealedContent);
    setIsDirty(false);
    setContentHydrated(true);
  }, [revealedContent]);

  const saveMut = useMutation({
    mutationFn: () =>
      isNew
        ? treeApi.createSecret(namespace, item.path, content)
        : treeApi.updateSecret(namespace, item.path, content),
    onSuccess: () => {
      invalidateItemDetailQueries(qc, namespace, item.path);
      void qc.invalidateQueries({
        queryKey: ["item-reveal", namespace, item.path],
      });
      invalidateTreeQueries(qc, namespace, item.path);
      setSavedContent(content);
      setIsDirty(false);
      setRevealed(true);
      setContentHydrated(true);
      if (isNew) {
        showToast("Secret created");
        navigate(`/ns/${namespace}/configs/${item.path}`, {
          replace: true,
          state: { revealSecret: true, secretContent: content },
        });
        return;
      }
      showToast("Secret saved");
    },
    onError: (e: Error) => pushApiError("Save failed", e),
  });

  const canSave =
    !item.deleted_at &&
    canEdit &&
    (isNew || revealedContent !== undefined || (revealed && contentHydrated)) &&
    (item.version === 0 || isDirty) &&
    hasEditorContent(content) &&
    isHealthy();

  const saveShortcut = useItemSaveShortcut({
    canSave,
    onSave: () => saveMut.mutate(),
  });
  saveShortcutMountRef.current = saveShortcut.onEditorMount;

  const handleReveal = () => {
    if (!revealed) {
      setRevealed(true);
    } else if (revealError) {
      void refetchReveal();
    }
  };

  const handleHide = () => {
    setRevealed(false);
    setContentHydrated(false);
    setPlaceholderContent(pickDummySecretContent());
    setContent("");
    setSavedContent("");
    setIsDirty(false);
  };

  const tabs: Array<{ id: Tab; label: string; icon: React.ReactNode }> =
    creating
      ? [{ id: "editor", label: "Editor", icon: null }]
      : [
          { id: "editor", label: "Editor", icon: null },
          {
            id: "history",
            label: "History",
            icon: <History className="h-3.5 w-3.5" />,
          },
          ...(permissions.canAudit
            ? [
                {
                  id: "audit" as const,
                  label: "Audit",
                  icon: <ScrollText className="h-3.5 w-3.5" />,
                },
              ]
            : []),
        ];

  const isDeleted = Boolean(item.deleted_at);
  const isSecretLoaded =
    isNew || revealedContent !== undefined || (revealed && contentHydrated);
  const showSave = !isDeleted && canEdit && isSecretLoaded;
  const revealedEditorValue = contentHydrated
    ? content
    : (revealedContent ?? "");

  return (
    <div className="flex h-full flex-col">
      {!creating && (
        <>
          <ItemHeader
            namespace={namespace}
            path={item.path}
            type="secret"
            version={item.version}
            tags={item.tags}
            showVersionSelector
            deletedAt={item.deleted_at}
            onDelete={
              canDeleteItem && !isDeleted
                ? () => setDeleteOpen(true)
                : undefined
            }
            onMove={
              canMoveItem && !isDeleted ? () => setMoveOpen(true) : undefined
            }
            onCopy={
              canCopyItem && !isDeleted ? () => setCopyOpen(true) : undefined
            }
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
        <div
          className={cn(
            "flex items-center gap-0.5 border-b px-4 dark:border-gray-700",
            creating && "py-2",
          )}
        >
          {!creating &&
            tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={cn(
                  "flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors",
                  activeTab === t.id
                    ? "border-brand-500 text-brand-700 dark:text-brand-300"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400",
                )}
              >
                {t.icon}
                {t.label}
              </button>
            ))}

          <div className="flex-1" />

          {isDirty &&
            activeTab === "editor" &&
            !isDeleted &&
            isSecretLoaded && (
              <span className="mr-2 flex items-center gap-1.5 text-xs text-yellow-600 dark:text-yellow-400">
                <AlertTriangle className="h-3 w-3" />
                Unsaved changes
              </span>
            )}

          {activeTab === "history" ? (
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
          ) : activeTab === "audit" ? null : showSave ? (
            <ItemSaveButton
              label={creating ? "Create" : "Save"}
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
          {activeTab === "editor" && isDeleted && item.deleted_at && (
            <DeletedVersionNotice
              version={item.version}
              deletedAt={item.deleted_at}
              deletedBy={item.updater}
            />
          )}
          {activeTab === "editor" &&
            !isDeleted &&
            (!permissions.canRead ? (
              <PermissionDenied message="You do not have permission to view this secret." />
            ) : (
              <div className="relative flex min-h-0 flex-1 flex-col">
                {isSecretLoaded ? (
                  <MonacoEditor
                    key={
                      creating
                        ? "revealed-create"
                        : `revealed-${item.path}-${item.version}`
                    }
                    height="100%"
                    language="yaml"
                    theme={monacoTheme}
                    value={revealedEditorValue}
                    onMount={handleSecretEditorMount}
                    onChange={(v) => {
                      if (!canEdit) return;
                      const next = v ?? "";
                      setContent(next);
                      setIsDirty(next !== savedContent);
                    }}
                    options={yamlEditorOptions(!canEdit)}
                  />
                ) : (
                  <>
                    <div className="min-h-0 flex-1 pointer-events-none select-none blur-[3px]">
                      <MonacoEditor
                        key={
                          creating
                            ? "placeholder-create"
                            : `placeholder-${item.path}-${item.version}`
                        }
                        height="100%"
                        language="yaml"
                        theme={monacoTheme}
                        value={placeholderContent}
                        options={yamlEditorOptions(true)}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleReveal}
                      disabled={revealing}
                      className={cn(
                        "absolute inset-0 z-10 flex cursor-pointer items-center justify-center",
                        "bg-gray-900/15 transition-colors",
                        "hover:bg-gray-900/25 dark:bg-gray-950/20 dark:hover:bg-gray-950/30",
                        revealing && "cursor-wait",
                      )}
                    >
                      <span className="rounded-md bg-gray-900/80 px-4 py-2 text-sm font-medium text-white shadow-lg dark:bg-gray-800/90">
                        {revealing
                          ? "Loading secret value…"
                          : revealError
                            ? "Failed to load secret — click to retry"
                            : "Click to reveal secret value"}
                      </span>
                    </button>
                  </>
                )}

                {isSecretLoaded && !isNew && (
                  <button
                    type="button"
                    onClick={handleHide}
                    title="Hide secret value"
                    aria-label="Hide secret value"
                    className={cn(
                      "absolute right-3 top-3 z-10 rounded-md p-1.5",
                      "bg-gray-800/90 text-gray-300 shadow-md ring-1 ring-gray-700/80",
                      "hover:bg-gray-700 hover:text-white",
                    )}
                  >
                    <EyeOff className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          {activeTab === "history" && (
            <ItemHistoryTab
              namespace={namespace}
              path={item.path}
              itemType="secret"
              currentVersion={item.version}
              canTag={permissions.canTag}
              isSelected={isHistorySelected}
              onToggle={toggleHistory}
              onDiffWithCurrent={handleDiffWithCurrent}
              diffPair={diffPair}
              onCloseDiff={() => setDiffPair(null)}
              onSwapDiff={() =>
                setDiffPair((p) => p && { from: p.to, to: p.from })
              }
            />
          )}
          {activeTab === "audit" && (
            <ItemAuditTab
              namespace={namespace}
              path={item.path}
              type="secret"
            />
          )}
        </div>
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
        type="secret"
        open={moveOpen}
        onClose={() => setMoveOpen(false)}
      />

      <LocationDialog
        mode="copy"
        namespace={namespace}
        path={item.path}
        type="secret"
        tags={item.tags}
        open={copyOpen}
        onClose={() => setCopyOpen(false)}
      />
    </div>
  );
}
