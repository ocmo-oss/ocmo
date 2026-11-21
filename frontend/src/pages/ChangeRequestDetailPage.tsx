import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronLeft, Copy, Info, Pencil } from "lucide-react";
import { changeRequestsApi } from "../api/changeRequests";
import { treeApi } from "../api/tree";
import { useAuth } from "../auth/useAuth";
import { useItemPermissions } from "../hooks/useItemPermissions";
import { useItemSaveShortcut } from "../hooks/useItemSaveShortcut";
import { Button } from "../components/ui/Button";
import { Tooltip } from "../components/ui/Tooltip";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { Input } from "../components/ui/Input";
import { cn } from "../components/ui/cn";
import { pushApiError } from "../store/notifications";
import { showToast } from "../components/ui/Toast";
import { formatUserDateTime } from "../lib/datetime";
import { pathSegments } from "../lib/paths";
import {
  CHANGE_REQUEST_EDITOR_HEIGHT,
  ChangeRequestDiffEditor,
} from "../components/changeRequests/ChangeRequestDiffEditor";
import { ChangeRequestDiscussion } from "../components/changeRequests/ChangeRequestDiscussion";
import { ResolvePanel } from "../components/resolve/ResolvePanel";
import { useConfigYamlSchema } from "../hooks/useConfigYamlSchema";
import type { ChangeRequest } from "../api/types";
import {
  parseCrLineHash,
  type CrLineRange,
} from "../lib/changeRequestLineRefs";
import { ChangeRequestStatusBadge } from "../lib/changeRequestStatus";
import {
  changeRequestDetailHref,
  changeRequestRefLabel,
} from "../lib/changeRequestRoutes";
import {
  changeRequestDataFingerprint,
  changeRequestRefetchInterval,
  useChangeRequestPageSync,
} from "../lib/changeRequestLiveSync";

function DiffModeSwitch({
  value,
  onChange,
  showLatest,
}: {
  value: "base" | "latest";
  onChange: (mode: "base" | "latest") => void;
  showLatest: boolean;
}) {
  return (
    <div
      className="inline-flex shrink-0 rounded-md border border-slate-300 p-0.5 text-xs dark:border-gray-600"
      role="group"
      aria-label="Diff comparison mode"
    >
      <button
        type="button"
        className={cn(
          "rounded px-2.5 py-1 font-medium transition-colors",
          value === "base"
            ? "bg-brand-600 text-white"
            : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200",
        )}
        onClick={() => onChange("base")}
      >
        Base → CR
      </button>
      {showLatest && (
        <button
          type="button"
          className={cn(
            "rounded px-2.5 py-1 font-medium transition-colors",
            value === "latest"
              ? "bg-brand-600 text-white"
              : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200",
          )}
          onClick={() => onChange("latest")}
        >
          Latest → CR
        </button>
      )}
    </div>
  );
}

function editorLanguage(nodeType: ChangeRequest["node_type"]): string {
  if (nodeType === "secret") return "plaintext";
  return "yaml";
}

export function ChangeRequestDetailPage({
  namespace,
  path,
  crNumber,
}: {
  namespace: string;
  path: string;
  crNumber: number;
}) {
  const number = crNumber;
  const qc = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const { whoami } = useAuth();
  const [highlightLineRange, setHighlightLineRange] =
    useState<CrLineRange | null>(null);
  const [diffAgainst, setDiffAgainst] = useState<"base" | "latest">("base");
  const [editorContent, setEditorContent] = useState("");
  const [contentDirty, setContentDirty] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [titleEditOpen, setTitleEditOpen] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [resolveMounted, setResolveMounted] = useState(false);
  const [resolveOpen, setResolveOpen] = useState(false);

  const crVersionRef = useMemo(() => `~${number}`, [number]);
  const { isJsonSchemaMode } = useConfigYamlSchema({
    namespace,
    path,
    versionRef: crVersionRef,
    editorContent,
  });

  const crFingerprintRef = useRef("");
  const { pageActive } = useChangeRequestPageSync(namespace, path, number);

  const { data: cr, isLoading } = useQuery({
    queryKey: ["change-request", namespace, path, number],
    queryFn: () => changeRequestsApi.get(namespace!, path, number, true),
    enabled: !!namespace && !!path && number > 0,
    refetchInterval: (query) =>
      changeRequestRefetchInterval(
        (query.state.data as ChangeRequest | undefined)?.status,
        pageActive,
      ),
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (!cr || cr.status !== "open") return;
    const fp = changeRequestDataFingerprint(cr);
    if (crFingerprintRef.current && crFingerprintRef.current !== fp) {
      void qc.invalidateQueries({
        queryKey: ["change-request-diff", namespace, path, number],
      });
    }
    crFingerprintRef.current = fp;
  }, [cr, namespace, path, number, qc]);

  const permissions = useItemPermissions(
    namespace,
    path,
    cr?.node_type ?? "config",
    !!cr,
  );

  const actorId = useMemo(() => {
    if (!whoami) return "";
    return whoami.display_name ?? whoami.identifier ?? "";
  }, [whoami]);

  const isAuthor = Boolean(cr && actorId && cr.created_by === actorId);
  const canEditContent =
    cr?.status === "open" && isAuthor && permissions.canRead;

  const showLatestDiff = Boolean(cr && cr.base_version !== cr.latest_version);

  const scrollToCrEditor = useCallback(() => {
    document
      .querySelector(".change-request-diff-editor")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const goToCrLines = useCallback(
    (hashFragment: string) => {
      const parsed = parseCrLineHash(hashFragment);
      if (!parsed) return;
      setHighlightLineRange(parsed);
      void navigate(
        {
          pathname: location.pathname,
          search: location.search,
          hash: hashFragment.replace(/^#/, ""),
        },
        { replace: false },
      );
      scrollToCrEditor();
    },
    [navigate, location.pathname, location.search, scrollToCrEditor],
  );

  useEffect(() => {
    const parsed = parseCrLineHash(location.hash);
    if (parsed) {
      setHighlightLineRange(parsed);
    }
  }, [location.hash]);

  useEffect(() => {
    if (!showLatestDiff && diffAgainst === "latest") {
      setDiffAgainst("base");
    }
  }, [showLatestDiff, diffAgainst]);

  const { data: baseDiff } = useQuery({
    queryKey: ["change-request-diff", namespace, path, number, "base"],
    queryFn: () =>
      changeRequestsApi.diff(
        namespace!,
        path,
        number,
        "base",
        cr?.node_type === "secret",
      ),
    enabled: !!cr && canEditContent,
  });

  const baseContent = baseDiff?.from.content ?? "";
  const contentMatchesBase =
    canEditContent && baseDiff !== undefined && editorContent === baseContent;

  const {
    data: diff,
    isLoading: diffLoading,
    isError: diffError,
    error: diffQueryError,
  } = useQuery({
    queryKey: ["change-request-diff", namespace, path, number, diffAgainst],
    queryFn: () =>
      changeRequestsApi.diff(
        namespace!,
        path,
        number,
        diffAgainst,
        cr?.node_type === "secret",
      ),
    enabled: !!cr,
  });

  const fromText = diff?.from.content ?? "";

  useEffect(() => {
    if (!cr || contentDirty) return;
    const next = diff?.to.content ?? cr.content ?? "";
    setEditorContent(next);
    setContentDirty(false);
  }, [cr, contentDirty, diff?.to.content, diffAgainst, number]);

  const saveContentMut = useMutation({
    mutationFn: (body: string) =>
      changeRequestsApi.update(namespace!, path, number, body),
    onSuccess: () => {
      setContentDirty(false);
      void qc.invalidateQueries({
        queryKey: ["change-request", namespace, path, number],
      });
      void qc.invalidateQueries({
        queryKey: ["change-request-diff", namespace, path, number],
      });
      showToast("Change request saved");
    },
    onError: (e: Error) => pushApiError("Save failed", e),
  });

  const canSaveCrContent =
    canEditContent && contentDirty && !contentMatchesBase && !resolveMounted;

  const saveShortcut = useItemSaveShortcut({
    canSave: canSaveCrContent,
    onSave: () => saveContentMut.mutate(editorContent),
    canFocusShortcut: canEditContent && contentDirty && !resolveMounted,
  });

  const saveShortcutMountRef = useRef(saveShortcut.onEditorMount);
  saveShortcutMountRef.current = saveShortcut.onEditorMount;

  const handleModifiedEditorMount = useCallback(
    (
      editorInstance: import("monaco-editor").editor.IStandaloneCodeEditor,
      monaco: typeof import("monaco-editor"),
    ) => {
      saveShortcutMountRef.current(editorInstance, monaco);
    },
    [],
  );

  const titleMut = useMutation({
    mutationFn: (title: string) =>
      changeRequestsApi.patchMetadata(namespace!, path, number, { title }),
    onSuccess: () => {
      setTitleEditOpen(false);
      void qc.invalidateQueries({
        queryKey: ["change-request", namespace, path, number],
      });
      showToast("Title updated");
    },
    onError: (e: Error) => pushApiError("Title update failed", e),
  });

  const approveMut = useMutation({
    mutationFn: () => changeRequestsApi.approve(namespace!, path, number),
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: ["change-request", namespace, path, number],
      });
      showToast("Approved");
    },
    onError: (e: Error) => pushApiError("Approve failed", e),
  });

  const unapproveMut = useMutation({
    mutationFn: () => changeRequestsApi.unapprove(namespace!, path, number),
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: ["change-request", namespace, path, number],
      });
      showToast("Approval removed");
    },
    onError: (e: Error) => pushApiError("Remove approval failed", e),
  });

  const rejectMut = useMutation({
    mutationFn: (reason: string) =>
      changeRequestsApi.reject(namespace!, path, number, reason),
    onSuccess: () => {
      setRejectOpen(false);
      setRejectReason("");
      void qc.invalidateQueries({
        queryKey: ["change-request", namespace, path, number],
      });
      showToast("Change request rejected");
    },
    onError: (e: Error) => pushApiError("Reject failed", e),
  });

  const applyMut = useMutation({
    mutationFn: () => changeRequestsApi.apply(namespace!, path, number),
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: ["change-request", namespace, path, number],
      });
      void treeApi.get(namespace!, path).then(() => {
        void qc.invalidateQueries({ queryKey: ["item", namespace, path] });
      });
      showToast("Change request applied");
    },
    onError: (e: Error) => pushApiError("Apply failed", e),
  });

  const copyProposedContent = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(editorContent);
      showToast("Proposed content copied");
    } catch (e) {
      pushApiError(
        "Copy failed",
        e instanceof Error ? e : new Error("Copy failed"),
      );
    }
  }, [editorContent]);

  const openResolve = useCallback(() => {
    setResolveMounted(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setResolveOpen(true));
    });
  }, []);

  const closeResolve = useCallback(() => {
    setResolveOpen(false);
  }, []);

  const handleResolveTransitionEnd = useCallback(
    (e: React.TransitionEvent<HTMLDivElement>) => {
      if (e.target !== e.currentTarget || e.propertyName !== "transform") {
        return;
      }
      if (!resolveOpen) setResolveMounted(false);
    },
    [resolveOpen],
  );

  useEffect(() => {
    closeResolve();
  }, [namespace, path, number, closeResolve]);

  useEffect(() => {
    if (isJsonSchemaMode && resolveMounted) closeResolve();
  }, [isJsonSchemaMode, resolveMounted, closeResolve]);

  if (isLoading || !cr) {
    return <p className="p-4 text-sm text-gray-500">Loading change request…</p>;
  }

  const resourceUrl = `/ns/${namespace}/configs/${path}`;
  const resourceLabel = pathSegments(path).pop() ?? path;
  const displayTitle = cr.title.trim() || `Change request ~${cr.number}`;

  const showUpdated = cr.updated_at && cr.updated_at !== cr.created_at;
  const canRejectWriter = cr.status === "open" && permissions.canWrite;
  const canApply = cr.status === "open" && cr.can_apply && permissions.canWrite;
  const canShowCrResolve =
    cr.node_type === "config" && permissions.canResolve && !isJsonSchemaMode;

  const openTitleEdit = () => {
    setTitleDraft(cr.title);
    setTitleEditOpen(true);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Link
            to={resourceUrl}
            title={path}
            className={cn(
              "inline-flex max-w-[10rem] shrink-0 items-center gap-1 rounded-md border border-slate-200",
              "bg-surface-elevated px-2 py-1 text-xs font-medium text-slate-700 shadow-sm",
              "hover:bg-slate-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700",
            )}
          >
            <ArrowLeft className="h-3.5 w-3.5 shrink-0" aria-hidden />
            <span className="truncate">{resourceLabel}</span>
          </Link>
          <div className="flex min-w-0 flex-1 items-center gap-1.5">
            <h1
              className="truncate text-base font-semibold text-gray-900 dark:text-gray-100"
              title={displayTitle}
            >
              {displayTitle}
            </h1>
            {cr.status === "open" && isAuthor && (
              <button
                type="button"
                onClick={openTitleEdit}
                className="shrink-0 rounded p-1 text-gray-500 hover:bg-slate-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                aria-label="Edit change request title"
              >
                <Pencil className="h-4 w-4" />
              </button>
            )}
            <ChangeRequestStatusBadge status={cr.status} />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {cr.status === "open" && canEditContent && contentDirty && (
            <Tooltip
              content={saveShortcut.enterHint}
              open={saveShortcut.showEnterHint}
              showOnHover={false}
              side="bottom"
              align="end"
            >
              <Button
                ref={saveShortcut.buttonRef}
                size="sm"
                loading={saveContentMut.isPending}
                disabled={contentMatchesBase}
                title={
                  contentMatchesBase
                    ? "Content must differ from the base version"
                    : undefined
                }
                onClick={() => saveContentMut.mutate(editorContent)}
                onKeyDown={saveShortcut.handleButtonKeyDown}
              >
                Save
              </Button>
            </Tooltip>
          )}
          {canShowCrResolve && !resolveMounted && (
            <Button
              variant="primary"
              size="sm"
              onClick={openResolve}
              className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
              title={
                contentDirty
                  ? `Resolve ${path}@${crVersionRef} including unsaved edits`
                  : `Resolve ${path}@${crVersionRef}`
              }
            >
              Resolve
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
            </Button>
          )}
          {!resolveMounted && (
            <DiffModeSwitch
              value={diffAgainst}
              onChange={setDiffAgainst}
              showLatest={showLatestDiff}
            />
          )}
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
          <div className="min-h-0 min-w-0 flex-1 overflow-y-auto">
            <div
              className="flex min-h-0 flex-col border-b border-gray-200 dark:border-gray-700"
              style={{ minHeight: CHANGE_REQUEST_EDITOR_HEIGHT }}
            >
              {diffLoading && (
                <Skeleton className="m-4 h-[min(42vh,400px)] w-full" />
              )}
              {diffError && (
                <p className="p-4 text-sm text-red-600 dark:text-red-400">
                  Failed to load diff.
                  {diffQueryError instanceof Error && diffQueryError.message
                    ? ` ${diffQueryError.message}`
                    : null}
                </p>
              )}
              {!diffLoading && !diffError && diff && (
                <div
                  className="relative w-full"
                  style={{ height: CHANGE_REQUEST_EDITOR_HEIGHT }}
                >
                  <div className="absolute right-2 top-2 z-10">
                    <Tooltip content="Copy proposed content (not the diff)">
                      <Button
                        variant="secondary"
                        size="sm"
                        className="shadow-sm"
                        onClick={() => void copyProposedContent()}
                        aria-label="Copy proposed content"
                      >
                        <Copy className="h-3.5 w-3.5" aria-hidden />
                      </Button>
                    </Tooltip>
                  </div>
                  <ChangeRequestDiffEditor
                    key={`${number}-${diffAgainst}`}
                    className="h-full w-full"
                    height={CHANGE_REQUEST_EDITOR_HEIGHT}
                    namespace={namespace}
                    configPath={path}
                    enableYamlCompletion={cr.node_type === "config"}
                    editorContent={editorContent}
                    original={fromText}
                    modified={editorContent}
                    language={editorLanguage(cr.node_type)}
                    readOnly={!canEditContent}
                    highlightLineRange={highlightLineRange}
                    onModifiedChange={(value) => {
                      setEditorContent(value);
                      setContentDirty(
                        value !== (diff.to.content ?? cr.content ?? ""),
                      );
                    }}
                    onModifiedEditorMount={handleModifiedEditorMount}
                  />
                </div>
              )}
              {!diffLoading && !diffError && !diff && (
                <p className="p-4 text-sm text-gray-500">No diff data.</p>
              )}
            </div>

            <ChangeRequestDiscussion
              namespace={namespace}
              path={path}
              number={number}
              pageActive={pageActive}
              onLineRefClick={goToCrLines}
              canComment={cr.status === "open"}
              changeRequest={cr}
            />
          </div>

          <aside className="flex w-full shrink-0 flex-col gap-3 overflow-y-auto border-l border-gray-200 p-4 dark:border-gray-700 lg:w-72">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Change request
            </p>
            {cr.status === "open" && (
              <div className="flex flex-col gap-2">
                {cr.can_approve && (
                  <Button
                    variant="outline-success"
                    size="sm"
                    className="w-full"
                    onClick={() => approveMut.mutate()}
                    disabled={approveMut.isPending}
                  >
                    Approve
                  </Button>
                )}
                {cr.can_unapprove && (
                  <Button
                    variant="outline-warning"
                    size="sm"
                    className="w-full"
                    onClick={() => unapproveMut.mutate()}
                    disabled={unapproveMut.isPending}
                  >
                    Remove approval
                  </Button>
                )}
                {(canRejectWriter || canApply) && (
                  <div className="flex gap-2">
                    {canRejectWriter && (
                      <Button
                        variant="outline-danger"
                        size="sm"
                        className="min-w-0 flex-1"
                        onClick={() => setRejectOpen(true)}
                        disabled={rejectMut.isPending}
                      >
                        Reject
                      </Button>
                    )}
                    {canApply && (
                      <Button
                        variant="outline-primary"
                        size="sm"
                        className="min-w-0 flex-1"
                        onClick={() => applyMut.mutate()}
                        disabled={applyMut.isPending}
                      >
                        Apply
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}

            {cr.status === "open" && (
              <p className="text-[11px] leading-snug text-amber-800 dark:text-amber-200">
                If applied, this change will be published as version{" "}
                <span className="font-mono font-semibold">
                  {cr.projected_version_on_apply}
                </span>
                .
              </p>
            )}

            <div className="space-y-2 rounded border border-gray-200 p-3 text-sm dark:border-gray-700">
              <p>
                <span className="text-[11px] text-gray-500">ID</span>
                <br />
                <span className="inline-flex items-center gap-1">
                  <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                    ~{cr.number}
                  </code>
                  <Tooltip
                    side="left"
                    align="start"
                    content={
                      <span className="block max-w-[15rem]">
                        Other change requests can reference this one using ref{" "}
                        <span className="font-mono text-gray-800 dark:text-gray-200">
                          ~{cr.number}
                        </span>{" "}
                        in YAML, for example{" "}
                        <span className="font-mono text-gray-800 dark:text-gray-200">
                          {path}@~{cr.number}
                        </span>
                        .
                      </span>
                    }
                  >
                    <button
                      type="button"
                      className="rounded p-0.5 text-gray-400 hover:bg-slate-100 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
                      aria-label="How to reference this change request"
                    >
                      <Info className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </Tooltip>
                </span>
              </p>
              <p>
                <span className="text-[11px] text-gray-500">Resource</span>
                <br />
                <span className="break-all font-mono text-xs">{path}</span>
              </p>
              <p>
                <span className="text-[11px] text-gray-500">Author</span>
                <br />
                <span className="text-xs">{cr.created_by}</span>
              </p>
              <p>
                <span className="text-[11px] text-gray-500">Created</span>
                <br />
                <span className="text-xs">
                  {formatUserDateTime(cr.created_at)}
                </span>
              </p>
              {showUpdated && (
                <p>
                  <span className="text-[11px] text-gray-500">
                    Last updated
                  </span>
                  <br />
                  <span className="text-xs">
                    {formatUserDateTime(cr.updated_at)}
                  </span>
                </p>
              )}
              <p>
                <span className="text-[11px] text-gray-500">Base version</span>
                <br />
                <span className="font-mono text-xs">v{cr.base_version}</span>
                {cr.base_superseded && (
                  <span className="mt-0.5 block text-[11px] text-amber-700 dark:text-amber-300">
                    Newer version exists (v{cr.latest_version})
                  </span>
                )}
              </p>
              <p>
                <span className="text-[11px] text-gray-500">Approvals</span>
                <br />
                <span className="text-xs">
                  {cr.approval_count} / {cr.required_approvals}
                </span>
              </p>
              {(cr.depends_on?.length ?? 0) > 0 && (
                <p>
                  <span className="text-[11px] text-gray-500">Depends on</span>
                  <ul className="mt-0.5 space-y-1">
                    {cr.depends_on.map((ref) => (
                      <li key={`dep-${ref.path}@~${ref.number}`}>
                        <Link
                          to={changeRequestDetailHref(namespace, ref)}
                          className="break-all font-mono text-xs text-brand-700 hover:underline dark:text-brand-300"
                        >
                          {changeRequestRefLabel(ref.path, ref.number)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </p>
              )}
              {(cr.referenced_by?.length ?? 0) > 0 && (
                <p>
                  <span className="text-[11px] text-gray-500">
                    Referenced by
                  </span>
                  <ul className="mt-0.5 space-y-1">
                    {cr.referenced_by.map((ref) => (
                      <li key={`ref-${ref.path}@~${ref.number}`}>
                        <Link
                          to={changeRequestDetailHref(namespace, ref)}
                          className="break-all font-mono text-xs text-brand-700 hover:underline dark:text-brand-300"
                        >
                          {changeRequestRefLabel(ref.path, ref.number)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </p>
              )}
              {cr.status === "applied" && (
                <>
                  {cr.applied_by && (
                    <p>
                      <span className="text-[11px] text-gray-500">
                        Applied by
                      </span>
                      <br />
                      <span className="text-xs">{cr.applied_by}</span>
                    </p>
                  )}
                  {cr.applied_version != null && (
                    <p>
                      <span className="text-[11px] text-gray-500">
                        Applied as version
                      </span>
                      <br />
                      <span className="font-mono text-xs">
                        v{cr.applied_version}
                      </span>
                    </p>
                  )}
                </>
              )}
            </div>

            {(cr.issues?.length ?? 0) > 0 && (
              <div className="rounded border border-amber-200 bg-amber-50 p-3 dark:border-amber-900/50 dark:bg-amber-950/30">
                <h2 className="text-xs font-semibold text-amber-900 dark:text-amber-100">
                  Known issues
                </h2>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px] leading-snug text-amber-900 dark:text-amber-200">
                  {cr.issues!.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </aside>
        </div>

        {resolveMounted && canShowCrResolve && (
          <div
            className={cn(
              "absolute inset-0 z-20 transition-transform duration-300 ease-in-out",
              resolveOpen ? "translate-x-0" : "translate-x-full",
            )}
            onTransitionEnd={handleResolveTransitionEnd}
          >
            <ResolvePanel
              namespace={namespace}
              path={path}
              versionRef={crVersionRef}
              content={editorContent}
              isDirty={contentDirty}
              allowMarkStable={false}
              onClose={closeResolve}
            />
          </div>
        )}
      </div>

      <Modal
        open={titleEditOpen}
        onClose={() => setTitleEditOpen(false)}
        title="Change request title"
      >
        <Input
          value={titleDraft}
          onChange={(e) => setTitleDraft(e.target.value)}
          placeholder={`Change request ~${cr.number}`}
          maxLength={200}
          autoFocus
        />
        <div className="mt-4 flex justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setTitleEditOpen(false)}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            loading={titleMut.isPending}
            onClick={() => titleMut.mutate(titleDraft.trim())}
          >
            Save
          </Button>
        </div>
      </Modal>

      <Modal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title="Reject change request"
      >
        <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">
          Optional reason for rejection:
        </p>
        <textarea
          className="mb-3 w-full rounded border border-gray-300 p-2 text-sm dark:border-gray-600 dark:bg-gray-900"
          rows={3}
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
        <div className="flex justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setRejectOpen(false)}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            size="sm"
            loading={rejectMut.isPending}
            onClick={() => rejectMut.mutate(rejectReason)}
          >
            Reject
          </Button>
        </div>
      </Modal>
    </div>
  );
}
