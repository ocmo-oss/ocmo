import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import MonacoEditor from "@monaco-editor/react";
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  FileText,
  Info,
  Play,
} from "lucide-react";
import { fetchAuthenticatedText } from "../../api/client";
import type {
  ResolveResponse,
  ResolveArtifact,
  ResolvedParameter,
} from "../../api/types";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Skeleton } from "../ui/Skeleton";
import { pushNotification } from "../../store/notifications";
import { showToast } from "../ui/Toast";
import { CastFormatSelector } from "./CastFormatSelector";
import { CastOptionsForm } from "./CastOptionsForm";
import { VyshyvankaPatternBand } from "./VyshyvankaPatternBand";
import { useMonacoEditorTheme } from "../../hooks/useMonacoEditorTheme";
import { emptyResolveArtifactsMessage } from "../../lib/resolveTargetLabel";
import { cn } from "../ui/cn";
import { useResolveWorkflow } from "./useResolveWorkflow";
import { FOCUS_TRANSITION_MS } from "../editor/focus/constants";

interface ResolvedArtifact extends ResolveArtifact {
  content: string;
}

function monacoLanguage(cast: string): string {
  switch (cast.toLowerCase()) {
    case "yaml":
    case "yml":
      return "yaml";
    case "json":
      return "json";
    case "python":
      return "python";
    default:
      return "plaintext";
  }
}

function ParameterField({
  name,
  param,
  value,
  error,
  onChange,
}: {
  name: string;
  param: ResolvedParameter;
  value: string;
  error?: string;
  onChange: (v: string) => void;
}) {
  const typeLabel =
    param.type === "projected"
      ? "Auto-computed"
      : param.type === "secret"
        ? "Secret reference"
        : param.type === "dynamic"
          ? "User input"
          : param.type;

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-gray-700 dark:text-gray-200">
          {name}
        </span>
        <Badge variant="default">{typeLabel}</Badge>
      </div>
      {param.description && (
        <p className="text-[10px] leading-snug text-gray-400">
          {param.description}
        </p>
      )}
      {param.type === "dynamic" ? (
        <>
          <input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={
              param.declared_default != null
                ? String(param.declared_default)
                : undefined
            }
            aria-invalid={Boolean(error)}
            className={cn(
              "w-full rounded border bg-surface-elevated px-2 py-1 font-mono text-[11px] dark:bg-gray-800 dark:text-gray-200",
              error
                ? "border-red-400 dark:border-red-500"
                : "border-slate-300 dark:border-gray-700",
            )}
          />
          {error && (
            <p className="text-[10px] leading-snug text-red-500">{error}</p>
          )}
        </>
      ) : (
        <p className="rounded bg-surface px-2 py-1 font-mono text-[10px] text-gray-600 dark:bg-gray-900 dark:text-gray-300">
          {String(param.effective_value ?? "—")}
        </p>
      )}
    </div>
  );
}

function TraceViewer({ trace }: { trace: ResolveResponse["trace"] }) {
  const [open, setOpen] = useState(false);
  if (!trace || Object.keys(trace).length === 0) return null;

  return (
    <div className="shrink-0 border-t p-3 dark:border-gray-700">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5" />
        )}
        <Info className="h-3.5 w-3.5" />
        Trace ({Object.keys(trace).length})
      </button>
      {open && (
        <div className="mt-2 divide-y rounded border text-xs dark:divide-gray-700 dark:border-gray-700">
          {Object.entries(trace).map(([key, p]) => (
            <div key={key} className="flex items-center gap-2 px-2 py-1.5">
              <span className="min-w-0 flex-1 truncate font-mono">
                {p.path}
              </span>
              <Badge variant={p.resolve_role === "direct" ? "info" : "default"}>
                {p.resolve_role}
              </Badge>
              <span className="text-gray-400">
                {p.skipped ? "Not found" : `v${p.version}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ResolvedArtifactsViewer({
  result,
  mode = "config",
  versionRef,
  ignoreMissingTags = false,
  onArtifactsLoadingChange,
}: {
  result: ResolveResponse;
  mode?: "config" | "folder";
  versionRef?: string;
  ignoreMissingTags?: boolean;
  onArtifactsLoadingChange?: (loading: boolean) => void;
}) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const monacoTheme = useMonacoEditorTheme();

  const {
    data: artifacts,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["resolve-artifacts", result.artifacts.map((a) => a.url)],
    queryFn: async ({ signal }) => {
      const contents = await Promise.all(
        result.artifacts.map((a) => fetchAuthenticatedText(a.url, signal)),
      );
      return result.artifacts.map((artifact, index) => ({
        ...artifact,
        content: contents[index] ?? "",
      })) satisfies ResolvedArtifact[];
    },
    enabled: result.artifacts.length > 0,
    staleTime: 0,
    gcTime: 0,
  });

  useEffect(() => {
    onArtifactsLoadingChange?.(isLoading);
  }, [isLoading, onArtifactsLoadingChange]);

  if (result.artifacts.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center">
        <p className="max-w-sm text-sm text-gray-400">
          {emptyResolveArtifactsMessage({
            mode,
            ignoreMissingTags,
            versionRef,
          })}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-3 p-4">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-full w-full" />
      </div>
    );
  }

  if (error) {
    const msg =
      error instanceof Error
        ? error.message
        : "Failed to load resolved content";
    return <p className="p-4 text-sm text-red-500">{msg}</p>;
  }

  if (!artifacts?.length) return null;

  const selected = artifacts[selectedIndex] ?? artifacts[0];
  const multiple = artifacts.length > 1;

  const downloadSelected = async () => {
    setDownloading(true);
    try {
      const blob = new Blob([selected.content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = selected.name;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Downloaded ${selected.name}`);
    } catch {
      pushNotification("error", "Download failed");
    } finally {
      setDownloading(false);
    }
  };

  const copySelected = async () => {
    try {
      await navigator.clipboard.writeText(selected.content);
      showToast("Copied to clipboard");
    } catch {
      pushNotification("error", "Copy failed");
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {multiple && (
        <nav className="flex shrink-0 gap-1 overflow-x-auto border-b px-2 py-1 dark:border-gray-700">
          {artifacts.map((artifact, index) => (
            <button
              key={`${artifact.name}-${artifact.version}-${artifact.url}`}
              type="button"
              onClick={() => setSelectedIndex(index)}
              className={cn(
                "flex shrink-0 items-center gap-1 rounded px-2 py-1 text-left text-[11px] transition-colors",
                index === selectedIndex
                  ? "bg-brand-50 font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300"
                  : "text-gray-500 hover:bg-slate-100 dark:text-gray-400 dark:hover:bg-gray-900",
              )}
            >
              <FileText className="h-3 w-3" />
              <span className="max-w-[12rem] truncate font-mono">
                {artifact.name}
              </span>
            </button>
          ))}
        </nav>
      )}

      <div className="flex shrink-0 items-center gap-2 border-b px-3 py-1.5 dark:border-gray-700">
        <p className="min-w-0 flex-1 truncate font-mono text-xs text-gray-800 dark:text-gray-200">
          {selected.name}
        </p>
        <Badge>{selected.cast}</Badge>
        <span className="text-[10px] text-gray-400">v{selected.version}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void copySelected()}
          title="Copy content"
        >
          <Copy className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          loading={downloading}
          onClick={() => void downloadSelected()}
          title="Download"
        >
          <Download className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="min-h-0 flex-1">
        <MonacoEditor
          height="100%"
          language={monacoLanguage(selected.cast)}
          theme={monacoTheme}
          value={selected.content}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            wordWrap: "on",
            accessibilitySupport: "on",
          }}
        />
      </div>
    </div>
  );
}

interface ResolvePanelProps {
  namespace: string;
  path: string;
  versionRef?: string;
  content?: string;
  isDirty?: boolean;
  onClose?: () => void;
  mode?: "config" | "folder";
  embedded?: boolean;
  variant?: "overlay" | "focus-split";
  /** When focus-split: stack result above options on narrow panes */
  splitOrientation?: "horizontal" | "vertical";
}

export function ResolvePanel({
  namespace,
  path,
  versionRef,
  content,
  isDirty = false,
  onClose,
  mode = "config",
  embedded = false,
  variant = "overlay",
  splitOrientation = "horizontal",
}: ResolvePanelProps) {
  const workflow = useResolveWorkflow({
    namespace,
    path,
    versionRef,
    content,
    isDirty,
    mode,
  });
  const {
    isFolder,
    useDraftResolve,
    castUnavailable,
    cast,
    setCast,
    castOpen,
    setCastOpen,
    castOptions,
    setCastOptions,
    castSchema,
    noCreds,
    setNoCreds,
    resolveMenuOpen,
    setResolveMenuOpen,
    dynamicParams,
    setDynamicParams,
    folderVersion,
    setFolderVersion,
    ignoreMissingTags,
    setIgnoreMissingTags,
    resolveResult,
    effectiveVersionRef,
    paramEntries,
    paramErrors,
    hasParamErrors,
    showParamsLoading,
    paramsIsError,
    paramsError,
    paramsData,
    resolveLabel,
    resolveMarkStableLabel,
    resolveActive,
    resolveMut,
    copyResolveCommand,
    clearArtifactsLoading,
  } = workflow;

  const showOverlayHeader = !embedded && variant === "overlay";
  const isFocusSplit = variant === "focus-split";
  const innerFlexDirection =
    isFocusSplit && splitOrientation === "vertical" ? "flex-col" : "flex-row";

  return (
    <div className="flex h-full w-full flex-col bg-surface-elevated dark:bg-gray-950">
      {showOverlayHeader && (
        <div className="flex shrink-0 items-center gap-3 border-b px-4 py-2 dark:border-gray-700">
          <Button
            variant="primary"
            size="sm"
            onClick={onClose}
            className="bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
          >
            Resolve
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            {useDraftResolve && <Badge variant="info">draft</Badge>}
            <span className="truncate text-xs text-gray-400">
              {effectiveVersionRef
                ? /^\d+$/.test(effectiveVersionRef)
                  ? `v${effectiveVersionRef}`
                  : effectiveVersionRef
                : "latest"}
            </span>
          </div>
        </div>
      )}

      <div
        className={cn(
          "flex min-h-0 flex-1 overflow-hidden",
          innerFlexDirection,
        )}
        style={
          isFocusSplit
            ? {
                transition: `flex-direction ${FOCUS_TRANSITION_MS}ms ease-in-out`,
              }
            : undefined
        }
      >
        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {resolveActive && (
            <VyshyvankaPatternBand
              active={resolveActive}
              className="absolute bottom-0 left-5 top-0 z-10"
            />
          )}
          {resolveResult ? (
            <ResolvedArtifactsViewer
              key={resolveResult.artifacts.map((a) => a.url).join("|")}
              result={resolveResult}
              mode={mode}
              versionRef={effectiveVersionRef}
              ignoreMissingTags={isFolder ? ignoreMissingTags : false}
              onArtifactsLoadingChange={clearArtifactsLoading}
            />
          ) : !resolveActive ? (
            <div className="flex h-full items-center justify-center p-6 text-center">
              <p className="max-w-sm text-sm text-gray-400">
                {isFolder
                  ? `Configure options on the right, then run ${resolveLabel.toLowerCase()} to preview output here.`
                  : `Configure parameters and options on the right, then run ${resolveLabel.toLowerCase()} to preview output here.`}
              </p>
            </div>
          ) : null}
          {resolveResult && <TraceViewer trace={resolveResult.trace} />}
        </div>

        <aside
          className={cn(
            "flex shrink-0 flex-col overflow-hidden dark:border-gray-700",
            isFocusSplit
              ? "w-full max-h-[45%] border-t dark:border-t-gray-700 sm:max-h-none sm:w-56 sm:border-l sm:border-t-0"
              : "w-72 border-l",
          )}
        >
          <div className="flex-1 space-y-4 overflow-y-auto p-3">
            {isFolder ? (
              <>
                <section>
                  <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                    Version
                  </h4>
                  <input
                    value={folderVersion}
                    onChange={(e) => setFolderVersion(e.target.value)}
                    placeholder="latest"
                    className="w-full rounded border border-slate-300 bg-surface-elevated px-2 py-1 font-mono text-[11px] dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                  />
                  <p className="mt-1 text-[10px] leading-snug text-gray-400">
                    Applied to all configs in this folder.
                  </p>
                </section>
                <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={ignoreMissingTags}
                    onChange={(e) => setIgnoreMissingTags(e.target.checked)}
                    className="rounded"
                  />
                  Ignore configs with missing tags
                </label>
              </>
            ) : (
              <section>
                <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                  Parameters
                </h4>
                {showParamsLoading && <Skeleton className="h-20 w-full" />}
                {paramsIsError && !paramsData && (
                  <p className="text-[11px] text-red-500">
                    {(paramsError as Error).message}
                  </p>
                )}
                {!showParamsLoading && paramEntries.length === 0 && (
                  <p className="text-[11px] text-gray-400">
                    No parameters for this config.
                  </p>
                )}
                <div className="space-y-3">
                  {paramEntries.map(([name, param]) => (
                    <ParameterField
                      key={name}
                      name={name}
                      param={param}
                      value={dynamicParams[name] ?? ""}
                      error={paramErrors[name]}
                      onChange={(v) =>
                        setDynamicParams((prev) => ({ ...prev, [name]: v }))
                      }
                    />
                  ))}
                </div>
              </section>
            )}

            <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
              <input
                type="checkbox"
                checked={noCreds}
                onChange={(e) => setNoCreds(e.target.checked)}
                className="rounded"
              />
              No credentials
            </label>

            {!castUnavailable && (
              <section>
                <button
                  type="button"
                  onClick={() => setCastOpen((o) => !o)}
                  className="mb-2 flex w-full items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400"
                >
                  {castOpen ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                  Cast
                </button>
                {castOpen && (
                  <div className="space-y-2">
                    <CastFormatSelector value={cast} onChange={setCast} />
                    {castSchema && (
                      <CastOptionsForm
                        schema={castSchema}
                        values={castOptions}
                        onChange={setCastOptions}
                      />
                    )}
                  </div>
                )}
              </section>
            )}
          </div>

          <div className="relative shrink-0 border-t p-3 dark:border-gray-700">
            <div className="flex">
              <Button
                variant="primary"
                size="sm"
                loading={resolveMut.isPending}
                disabled={hasParamErrors}
                onClick={() => resolveMut.mutate(false)}
                className="flex-1 rounded-r-none bg-green-600 hover:bg-green-700 dark:bg-green-600 dark:hover:bg-green-700"
              >
                <Play className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{resolveLabel}</span>
              </Button>
              <button
                type="button"
                onClick={() => setResolveMenuOpen((o) => !o)}
                className="rounded-r-md border border-l-0 border-green-700 bg-green-600 px-2 text-white hover:bg-green-700 dark:border-green-800"
                aria-label="Resolve options"
              >
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
            </div>
            {resolveMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setResolveMenuOpen(false)}
                />
                <div className="absolute bottom-full right-3 z-20 mb-1 w-52 rounded-md border bg-surface-elevated py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900">
                  <button
                    type="button"
                    className="flex w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-gray-800 disabled:opacity-50"
                    disabled={hasParamErrors}
                    onClick={() => resolveMut.mutate(false)}
                  >
                    {resolveLabel}
                  </button>
                  <button
                    type="button"
                    className="flex w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-gray-800 disabled:opacity-50"
                    disabled={hasParamErrors}
                    onClick={() => resolveMut.mutate(true)}
                  >
                    {resolveMarkStableLabel}
                  </button>
                  <div className="my-1 border-t dark:border-gray-700" />
                  <button
                    type="button"
                    className="flex w-full px-3 py-2 text-left text-xs text-gray-600 hover:bg-slate-100 dark:text-gray-300 dark:hover:bg-gray-800 disabled:opacity-50"
                    disabled={hasParamErrors}
                    onClick={() => void copyResolveCommand("curl")}
                  >
                    Copy curl command
                  </button>
                  <button
                    type="button"
                    className="flex w-full px-3 py-2 text-left text-xs text-gray-600 hover:bg-slate-100 dark:text-gray-300 dark:hover:bg-gray-800 disabled:opacity-50"
                    disabled={hasParamErrors}
                    onClick={() => void copyResolveCommand("cli")}
                  >
                    Copy CLI command
                  </button>
                  <button
                    type="button"
                    className="flex w-full px-3 py-2 text-left text-xs text-gray-600 hover:bg-slate-100 dark:text-gray-300 dark:hover:bg-gray-800 disabled:opacity-50"
                    disabled={hasParamErrors}
                    onClick={() => void copyResolveCommand("sdk")}
                  >
                    Copy SDK command
                  </button>
                </div>
              </>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
