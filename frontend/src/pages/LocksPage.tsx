import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { locksApi } from "../api/locks";
import { PathSearchCombobox } from "../components/diff/PathSearchCombobox";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { pushApiError } from "../store/notifications";
import { showToast } from "../components/ui/Toast";
import { cn } from "../components/ui/cn";
import type { Lock } from "../api/types";
import { QueryAccessGate } from "../components/QueryAccessGate";
import { PermissionDenied } from "../components/items/PermissionDenied";
import { useLockPermissions } from "../hooks/useLockPermissions";
import {
  formatUserDateTime,
  formatUserDateTimeRelative,
  isOptionalFutureLocalDateTimeInput,
  LOCK_EXPIRES_MIN_OFFSET_MS,
  minFutureLocalDateTimeInput,
} from "../lib/datetime";

function CreateLockModal({
  namespace,
  open,
  onClose,
}: {
  namespace: string;
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [path, setPath] = useState("");
  const [reason, setReason] = useState("");
  const [expiresAt, setExpiresAt] = useState("");

  const minExpiresAt = useMemo(
    () => minFutureLocalDateTimeInput(LOCK_EXPIRES_MIN_OFFSET_MS),
    [open],
  );
  const minExpiresDate = useMemo(
    () => new Date(Date.now() + LOCK_EXPIRES_MIN_OFFSET_MS),
    [open],
  );
  const expiresAtError =
    expiresAt && !isOptionalFutureLocalDateTimeInput(expiresAt, minExpiresDate)
      ? "Expiry must be at least 30 minutes from now"
      : undefined;

  const mut = useMutation({
    mutationFn: () =>
      locksApi.create(namespace, path.trim(), {
        reason,
        expires_at: expiresAt || undefined,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["locks", namespace] });
      showToast(`Lock created on "${path}"`);
      onClose();
      setPath("");
      setReason("");
      setExpiresAt("");
    },
    onError: (e: Error) => pushApiError("Failed to create lock", e),
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create lock"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={mut.isPending}
            disabled={!!expiresAtError}
            onClick={() => mut.mutate()}
          >
            Lock
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <PathSearchCombobox
          namespace={namespace}
          value={path}
          onInputChange={setPath}
          onSelect={(item) => setPath(item.path)}
          placeholder="folder/subfolder"
          emptyMessage="No matching tree paths"
        />
        <Input
          label="Reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Deploying…"
        />
        <Input
          label="Expires at (optional)"
          type="datetime-local"
          value={expiresAt}
          min={minExpiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
          error={expiresAtError}
        />
      </div>
    </Modal>
  );
}

function LockDetailModal({
  lock,
  onClose,
  onDelete,
  deleting,
  canDelete,
}: {
  lock: Lock;
  onClose: () => void;
  onDelete: () => void;
  deleting: boolean;
  canDelete: boolean;
}) {
  return (
    <Modal
      open
      title={`Lock: ${lock.path}`}
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          {canDelete && (
            <Button variant="danger" loading={deleting} onClick={onDelete}>
              <Trash2 className="h-4 w-4" /> Remove lock
            </Button>
          )}
        </>
      }
    >
      <div className="space-y-3 text-sm">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
          {[
            ["Path", lock.path],
            ["Locked by", lock.locked_by || "—"],
            ["Created", formatUserDateTime(lock.created_at)],
            ["Updated", formatUserDateTime(lock.updated_at)],
            [
              "Expires",
              lock.expires_at ? formatUserDateTime(lock.expires_at) : "Never",
            ],
          ].map(([k, v]) => (
            <Fragment key={String(k)}>
              <dt className="font-medium text-gray-500">{k}</dt>
              <dd className="font-mono text-xs break-all">{String(v)}</dd>
            </Fragment>
          ))}
        </dl>
        <div>
          <p className="font-medium text-gray-500 mb-1">Reason</p>
          <p className="rounded border bg-surface px-3 py-2 text-sm text-gray-800 dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-200">
            {lock.reason || "—"}
          </p>
        </div>
      </div>
    </Modal>
  );
}

export function LocksPage() {
  const { namespace, "*": splat } = useParams<{
    namespace: string;
    "*": string;
  }>();
  const lockPath = splat?.replace(/\/+$/, "") || "";
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  // Legacy ?path= deeplink → path-based URL
  useEffect(() => {
    const legacy = searchParams.get("path");
    if (!legacy || !namespace) return;
    navigate(`/ns/${namespace}/locks/${legacy}`, { replace: true });
  }, [searchParams, namespace, navigate]);

  const lockPermissions = useLockPermissions(namespace);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["locks", namespace],
    queryFn: ({ signal }) => locksApi.list(namespace!, { limit: 100 }, signal),
    enabled: !!namespace && lockPermissions.isReady && lockPermissions.canRead,
    staleTime: 15_000,
  });

  const fromList = data?.locks.find((l) => l.path === lockPath);

  const {
    data: fetchedLock,
    isLoading: detailLoading,
    isError: detailError,
  } = useQuery({
    queryKey: ["lock", namespace, lockPath],
    queryFn: ({ signal }) => locksApi.get(namespace!, lockPath, signal),
    enabled:
      !!namespace &&
      !!lockPath &&
      !fromList &&
      !!data &&
      lockPermissions.isReady &&
      lockPermissions.canRead,
    staleTime: 15_000,
    retry: false,
  });

  const selected = lockPath ? (fromList ?? fetchedLock ?? null) : null;

  const openLock = (path: string) => navigate(`/ns/${namespace}/locks/${path}`);
  const closeLock = () => navigate(`/ns/${namespace}/locks`);

  const deleteMut = useMutation({
    mutationFn: (lock: Lock) => locksApi.delete(namespace!, lock.path),
    onSuccess: (_, lock) => {
      void qc.invalidateQueries({ queryKey: ["locks", namespace] });
      void qc.removeQueries({ queryKey: ["lock", namespace, lock.path] });
      showToast(`Lock on "${lock.path}" removed`);
      if (lockPath === lock.path) closeLock();
    },
    onError: (e: Error) => pushApiError("Failed to remove lock", e),
  });

  if (!lockPermissions.isReady) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b px-6 py-4 dark:border-gray-700">
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="space-y-2 p-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!lockPermissions.canRead) {
    return (
      <PermissionDenied message="You do not have permission to view locks." />
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-4 dark:border-gray-700">
        <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          Locks — <span className="font-mono text-brand-600">{namespace}</span>
        </h1>
        {lockPermissions.canWrite && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="h-4 w-4" /> Create lock
          </Button>
        )}
      </div>

      <QueryAccessGate
        isLoading={isLoading}
        isError={isError}
        error={error}
        hasData={!!data}
        permissionDeniedMessage="You do not have permission to view locks."
        loadingFallback={
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        }
      >
        <div className="flex-1 overflow-auto">
          {data && (
            <table className="w-full table-fixed divide-y divide-slate-200 dark:divide-gray-800">
              <colgroup>
                <col className="w-[24%]" />
                <col className="w-[32%]" />
                <col className="w-[18%]" />
                <col className="w-[12%]" />
                <col className="w-[10%]" />
                <col className="w-[4%]" />
              </colgroup>
              <thead className="bg-surface dark:bg-gray-800/50 sticky top-0">
                <tr>
                  {[
                    "Path",
                    "Reason",
                    "Locked by",
                    "Created",
                    "Expires",
                    "",
                  ].map((h, i) => (
                    <th
                      key={h || `actions-${i}`}
                      className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-gray-500"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-surface-elevated dark:divide-gray-800/50 dark:bg-gray-900">
                {data.locks.map((lock) => (
                  <tr
                    key={lock.path}
                    className={cn(
                      "cursor-pointer hover:bg-slate-100 dark:hover:bg-gray-800/40",
                      lockPath === lock.path &&
                        "bg-brand-50/50 outline outline-2 outline-offset-[-2px] outline-brand-400 dark:bg-brand-900/20",
                    )}
                    onClick={() => openLock(lock.path)}
                  >
                    <td className="px-4 py-2.5 font-mono text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                      {lock.path}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-gray-600 dark:text-gray-400 truncate">
                      {lock.reason}
                    </td>
                    <td className="px-4 py-2.5 text-xs font-mono text-gray-700 dark:text-gray-300 truncate">
                      {lock.locked_by || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-400 truncate">
                      {formatUserDateTimeRelative(lock.created_at)}
                    </td>
                    <td className="px-4 py-2.5 truncate">
                      {lock.expires_at ? (
                        <Badge variant="warning">
                          expires {formatUserDateTimeRelative(lock.expires_at)}
                        </Badge>
                      ) : (
                        <span className="text-xs text-gray-400">Never</span>
                      )}
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      {lockPermissions.canDelete && (
                        <Button
                          variant="ghost"
                          size="sm"
                          loading={
                            deleteMut.isPending &&
                            deleteMut.variables?.path === lock.path
                          }
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteMut.mutate(lock);
                          }}
                          aria-label={`Remove lock on ${lock.path}`}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
                {data.locks.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-12 text-center text-sm text-gray-400"
                    >
                      No active locks
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </QueryAccessGate>

      {data && data.count > 0 && (
        <div className="border-t px-6 py-3 text-xs text-gray-500 dark:border-gray-700">
          {data.count} active lock{data.count === 1 ? "" : "s"}
        </div>
      )}

      <CreateLockModal
        namespace={namespace!}
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />

      {lockPath && selected && (
        <LockDetailModal
          lock={selected}
          onClose={closeLock}
          deleting={deleteMut.isPending}
          onDelete={() => deleteMut.mutate(selected)}
          canDelete={lockPermissions.canDelete}
        />
      )}

      {lockPath && !selected && (detailLoading || isLoading) && (
        <Modal open title={`Lock: ${lockPath}`} onClose={closeLock} size="lg">
          <Skeleton lines={4} className="h-6 w-full" />
        </Modal>
      )}

      {lockPath && !selected && !detailLoading && !isLoading && detailError && (
        <Modal open title={`Lock: ${lockPath}`} onClose={closeLock} size="lg">
          <p className="text-sm text-gray-500">No active lock at this path.</p>
        </Modal>
      )}
    </div>
  );
}
