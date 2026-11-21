import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { namespacesApi } from "../api/namespaces";
import { NamespaceConfigTagField } from "../components/namespace/NamespaceConfigTagField";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Skeleton } from "../components/ui/Skeleton";
import { QueryAccessGate } from "../components/QueryAccessGate";
import { PermissionDenied } from "../components/items/PermissionDenied";
import { useNamespacePermissions } from "../hooks/useNamespacePermissions";
import { pushApiError } from "../store/notifications";
import { showToast } from "../components/ui/Toast";
import { formatUserDateTime } from "../lib/datetime";
import { useDefaultNamespace } from "../store/defaultNamespace";
import { cn } from "../components/ui/cn";

function configDescriptionLink(
  namespace: string,
  path: string,
  suffix: string,
) {
  return (
    <>
      Version of{" "}
      <Link
        to={`/ns/${namespace}/configs/${path}`}
        className="font-mono text-brand-600 hover:underline dark:text-brand-400"
      >
        {path}
      </Link>{" "}
      config {suffix}
    </>
  );
}

export function NamespaceSettingsPage() {
  const { namespace } = useParams<{ namespace: string }>();
  const qc = useQueryClient();
  const nsPermissions = useNamespacePermissions(namespace);
  const {
    namespace: defaultNamespace,
    setDefaultNamespace,
    clearDefaultNamespace,
  } = useDefaultNamespace();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["namespace", namespace],
    queryFn: ({ signal }) => namespacesApi.get(namespace!, signal),
    enabled: !!namespace,
    staleTime: 30_000,
  });

  const [description, setDescription] = useState("");
  const [permTag, setPermTag] = useState("latest");
  const [webhookTag, setWebhookTag] = useState("latest");
  const [gitSyncTag, setGitSyncTag] = useState("latest");
  const [crEnabled, setCrEnabled] = useState(false);
  const [crRequiredApprovals, setCrRequiredApprovals] = useState(1);
  const [crAutoReject, setCrAutoReject] = useState(true);
  const [crMaxOpen, setCrMaxOpen] = useState(1);
  const [crResetApprovals, setCrResetApprovals] = useState(true);

  useEffect(() => {
    if (data) {
      setDescription(data.description ?? "");
      setPermTag(data.permissions_tag);
      setWebhookTag(data.webhooks_tag);
      setGitSyncTag(data.git_sync_tag);
      setCrEnabled(data.change_requests_enabled ?? false);
      setCrRequiredApprovals(data.change_requests_required_approvals ?? 1);
      setCrAutoReject(data.change_requests_auto_reject_on_new_version ?? true);
      setCrMaxOpen(data.change_requests_max_open_per_user_per_resource ?? 1);
      setCrResetApprovals(
        data.change_requests_reset_approvals_on_change ?? true,
      );
    }
  }, [data]);

  const mut = useMutation({
    mutationFn: () =>
      namespacesApi.update(namespace!, {
        description,
        permissions_tag: permTag,
        webhooks_tag: webhookTag,
        git_sync_tag: gitSyncTag,
        change_requests_enabled: crEnabled,
        change_requests_required_approvals: crRequiredApprovals,
        change_requests_auto_reject_on_new_version: crAutoReject,
        change_requests_max_open_per_user_per_resource: crMaxOpen,
        change_requests_reset_approvals_on_change: crResetApprovals,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["namespace", namespace] });
      void qc.invalidateQueries({ queryKey: ["namespaces"] });
      showToast("Settings saved");
    },
    onError: (e: Error) => pushApiError("Failed to save settings", e),
  });

  const readOnly = !nsPermissions.canWrite;

  if (!nsPermissions.isLoading && !nsPermissions.canWrite) {
    return (
      <PermissionDenied message="You do not have permission to view namespace settings." />
    );
  }

  return (
    <QueryAccessGate
      isLoading={isLoading}
      isError={isError}
      error={error}
      hasData={!!data}
      permissionDeniedMessage="You do not have permission to view namespace settings."
      notFoundMessage="Namespace not found."
      loadingFallback={
        <div className="flex h-full min-h-0 w-full flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-xl px-4 py-5">
              <Skeleton lines={6} className="h-10 w-full" />
            </div>
          </div>
        </div>
      }
    >
      <div className="flex h-full min-h-0 w-full flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-xl space-y-4 px-4 py-5">
            <h1 className="text-lg font-bold leading-tight text-gray-900 dark:text-gray-100">
              Namespace settings —{" "}
              <span className="font-mono text-brand-600">{namespace}</span>
            </h1>

            <div
              className={cn(
                "space-y-4",
                readOnly && "pointer-events-none opacity-80",
              )}
            >
              <Input
                label="Description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="py-1"
              />

              <div className="space-y-3">
                <NamespaceConfigTagField
                  namespace={namespace!}
                  path="_permissions"
                  label="Permissions config"
                  description={configDescriptionLink(
                    namespace!,
                    "_permissions",
                    "used to evaluate access policies",
                  )}
                  value={permTag}
                  onChange={setPermTag}
                />

                <NamespaceConfigTagField
                  namespace={namespace!}
                  path="_webhooks"
                  label="Webhooks config"
                  description={configDescriptionLink(
                    namespace!,
                    "_webhooks",
                    "used for webhook delivery configuration",
                  )}
                  value={webhookTag}
                  onChange={setWebhookTag}
                />

                <NamespaceConfigTagField
                  namespace={namespace!}
                  path="_git_sync"
                  label="Git sync config"
                  description={configDescriptionLink(
                    namespace!,
                    "_git_sync",
                    "used for Git synchronization configuration",
                  )}
                  value={gitSyncTag}
                  onChange={setGitSyncTag}
                />
              </div>

              <section
                aria-labelledby="namespace-cr-settings"
                className="space-y-3 rounded-md border border-slate-300 p-3 dark:border-gray-700"
              >
                <div id="namespace-cr-settings">
                  <p className="text-sm font-medium leading-tight text-gray-700 dark:text-gray-300">
                    Change requests
                  </p>
                  <p className="text-[11px] leading-snug text-gray-400">
                    Propose changes on configs, templates, and secrets before
                    publishing a new version.
                  </p>
                </div>

                <label className="flex cursor-pointer items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-px rounded border-slate-400 text-brand-600 focus:ring-brand-500 dark:border-gray-600"
                    checked={crEnabled}
                    onChange={(e) => setCrEnabled(e.target.checked)}
                  />
                  <span>
                    <span className="block text-xs font-medium leading-tight text-gray-700 dark:text-gray-300">
                      Enable change requests
                    </span>
                    <span className="mt-0.5 block text-[11px] leading-snug text-gray-500 dark:text-gray-400">
                      Readers can open change requests; writers can approve,
                      reject, and apply.
                    </span>
                  </span>
                </label>

                {crEnabled && (
                  <div className="space-y-3 border-t border-slate-200 pt-3 dark:border-gray-700">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                      Policy
                    </p>
                    <Input
                      label="Required approvals"
                      type="number"
                      min={0}
                      max={100}
                      value={String(crRequiredApprovals)}
                      onChange={(e) =>
                        setCrRequiredApprovals(Number(e.target.value) || 0)
                      }
                      className="py-1"
                    />
                    <Input
                      label="Max open change requests per user per resource"
                      type="number"
                      min={1}
                      max={100}
                      value={String(crMaxOpen)}
                      onChange={(e) =>
                        setCrMaxOpen(Number(e.target.value) || 1)
                      }
                      className="py-1"
                    />
                    <label className="flex cursor-pointer items-start gap-2">
                      <input
                        type="checkbox"
                        className="mt-px rounded border-slate-400 text-brand-600 focus:ring-brand-500 dark:border-gray-600"
                        checked={crAutoReject}
                        onChange={(e) => setCrAutoReject(e.target.checked)}
                      />
                      <span>
                        <span className="block text-xs font-medium leading-tight text-gray-700 dark:text-gray-300">
                          Auto-reject on new version
                        </span>
                        <span className="mt-0.5 block text-[11px] leading-snug text-gray-500 dark:text-gray-400">
                          Close open change requests when a new version is
                          published outside the CR flow.
                        </span>
                      </span>
                    </label>
                    <label className="flex cursor-pointer items-start gap-2">
                      <input
                        type="checkbox"
                        className="mt-px rounded border-slate-400 text-brand-600 focus:ring-brand-500 dark:border-gray-600"
                        checked={crResetApprovals}
                        onChange={(e) => setCrResetApprovals(e.target.checked)}
                      />
                      <span>
                        <span className="block text-xs font-medium leading-tight text-gray-700 dark:text-gray-300">
                          Reset approvals on content change
                        </span>
                        <span className="mt-0.5 block text-[11px] leading-snug text-gray-500 dark:text-gray-400">
                          Clear existing approvals when the change request body
                          is updated (not when only the base version changes).
                        </span>
                      </span>
                    </label>
                  </div>
                )}
              </section>
            </div>

            <label className="flex cursor-pointer items-start gap-2 rounded-md border border-slate-300 px-2.5 py-2 dark:border-gray-700">
              <input
                type="checkbox"
                className="mt-px rounded border-slate-400 text-brand-600 focus:ring-brand-500 dark:border-gray-600"
                checked={defaultNamespace === namespace}
                onChange={(e) => {
                  if (e.target.checked) {
                    setDefaultNamespace(namespace!);
                    showToast(`"${namespace}" is now your default namespace`);
                  } else {
                    clearDefaultNamespace();
                    showToast("Default namespace cleared");
                  }
                }}
              />
              <span>
                <span className="block text-xs font-medium leading-tight text-gray-700 dark:text-gray-300">
                  Default namespace
                </span>
                <span className="mt-0.5 block text-[11px] leading-snug text-gray-500 dark:text-gray-400">
                  Open this namespace automatically when you sign in or click
                  the OCMO logo.
                </span>
              </span>
            </label>

            <div className="rounded-md border p-2.5 text-[11px] leading-snug text-gray-400 dark:border-gray-700">
              <strong>Note:</strong> The active tag cannot be deleted while
              selected. To delete a tag, first point the namespace to a
              different version here.
            </div>
          </div>
        </div>

        <footer className="shrink-0 border-t bg-surface-elevated dark:border-gray-700 dark:bg-gray-900">
          <div className="mx-auto flex w-full max-w-xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
            <p className="text-[11px] leading-snug text-gray-400">
              Created: {formatUserDateTime(data?.created_at)}
              <span className="mx-1.5">·</span>
              Updated: {formatUserDateTime(data?.updated_at)}
            </p>
            {nsPermissions.canWrite && (
              <Button
                variant="primary"
                size="sm"
                loading={mut.isPending}
                onClick={() => mut.mutate()}
              >
                Save settings
              </Button>
            )}
          </div>
        </footer>
      </div>
    </QueryAccessGate>
  );
}
