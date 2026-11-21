import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { changeRequestsApi } from "../../api/changeRequests";
import type { ChangeRequest } from "../../api/types";
import { ChangeRequestStatusBadge } from "../../lib/changeRequestStatus";
import { useItemPermissions } from "../../hooks/useItemPermissions";
import { formatUserDateTime } from "../../lib/datetime";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { Skeleton } from "../ui/Skeleton";
import { cn } from "../ui/cn";
import { pushApiError } from "../../store/notifications";
import { showToast } from "../ui/Toast";

interface ChangeRequestsTabProps {
  namespace: string;
  path: string;
  itemType?: "config" | "template" | "secret";
}

function sortChangeRequests(items: ChangeRequest[]): ChangeRequest[] {
  return [...items].sort((a, b) => {
    const openA = a.status === "open" ? 0 : 1;
    const openB = b.status === "open" ? 0 : 1;
    if (openA !== openB) return openA - openB;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

function displayTitle(cr: ChangeRequest): string {
  const t = cr.title.trim();
  return t || `Change request ~${cr.number}`;
}

function crDetailHref(namespace: string, path: string, number: number): string {
  return `/ns/${namespace}/configs/${path}/change-requests/${number}`;
}

export function ChangeRequestsTab({
  namespace,
  path,
  itemType = "config",
}: ChangeRequestsTabProps) {
  const qc = useQueryClient();
  const permissions = useItemPermissions(namespace, path, itemType);
  const [selected, setSelected] = useState<Set<number>>(() => new Set());
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["change-requests", namespace, path],
    queryFn: () => changeRequestsApi.list(namespace, path),
  });

  const items = useMemo(
    () => sortChangeRequests(data?.items ?? []),
    [data?.items],
  );

  const openItems = useMemo(
    () => items.filter((cr) => cr.status === "open"),
    [items],
  );

  const canBulkReject = permissions.canWrite && !permissions.isLoading;

  const selectableOpen = useMemo(
    () => (canBulkReject ? openItems.map((cr) => cr.number) : []),
    [canBulkReject, openItems],
  );

  const allSelectableSelected =
    selectableOpen.length > 0 && selectableOpen.every((n) => selected.has(n));

  const toggleOne = (number: number, open: boolean) => {
    if (!open || !canBulkReject) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(number)) next.delete(number);
      else next.add(number);
      return next;
    });
  };

  const toggleAll = () => {
    if (!canBulkReject) return;
    setSelected(() =>
      allSelectableSelected ? new Set() : new Set(selectableOpen),
    );
  };

  const rejectMut = useMutation({
    mutationFn: async ({
      numbers,
      reason,
    }: {
      numbers: number[];
      reason: string;
    }) => {
      const results = await Promise.allSettled(
        numbers.map((n) =>
          changeRequestsApi.reject(namespace, path, n, reason),
        ),
      );
      const failed = results.filter((r) => r.status === "rejected");
      if (failed.length > 0) {
        throw new Error(
          `Failed to reject ${failed.length} of ${numbers.length} change request(s)`,
        );
      }
    },
    onSuccess: (_, { numbers }) => {
      setSelected(new Set());
      setRejectOpen(false);
      setRejectReason("");
      void qc.invalidateQueries({
        queryKey: ["change-requests", namespace, path],
      });
      showToast(
        numbers.length === 1
          ? "Change request rejected"
          : `${numbers.length} change requests rejected`,
      );
    },
    onError: (e: Error) => pushApiError("Reject failed", e),
  });

  const selectedOpen = useMemo(
    () => [...selected].filter((n) => openItems.some((cr) => cr.number === n)),
    [selected, openItems],
  );

  if (isLoading) {
    return (
      <div className="px-4 py-3">
        <Skeleton lines={4} />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="px-4 py-3 text-sm text-red-600 dark:text-red-400">
        Failed to load change requests.
      </p>
    );
  }

  if (items.length === 0) {
    return (
      <p className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
        No change requests for this item.
      </p>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {canBulkReject && selectedOpen.length > 0 && (
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-2 dark:border-gray-700">
          <span className="text-xs text-gray-600 dark:text-gray-400">
            {selectedOpen.length} selected
          </span>
          <Button
            variant="outline-danger"
            size="sm"
            onClick={() => setRejectOpen(true)}
          >
            Reject
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelected(new Set())}
          >
            Clear
          </Button>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
        <table className="w-full min-w-[44rem] text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500 dark:border-gray-700 dark:text-gray-400">
              {canBulkReject && (
                <th className="w-10 px-4 py-2.5">
                  <input
                    type="checkbox"
                    className="rounded border-gray-400 dark:border-gray-600"
                    checked={allSelectableSelected}
                    disabled={selectableOpen.length === 0}
                    onChange={toggleAll}
                    aria-label="Select all open change requests"
                  />
                </th>
              )}
              <th className={cn("py-2.5 pr-3", !canBulkReject && "pl-4")}>
                ID
              </th>
              <th className="py-2.5 pr-3">Title</th>
              <th className="py-2.5 pr-3">Author</th>
              <th className="py-2.5 pr-3">Status</th>
              <th className="py-2.5 pr-3">Approvals</th>
              <th className="py-2.5 pr-3">Base</th>
              <th className="py-2.5 pr-4">Created</th>
            </tr>
          </thead>
          <tbody>
            {items.map((cr) => {
              const title = displayTitle(cr);
              const isOpen = cr.status === "open";
              const approvalsMet = cr.approval_count >= cr.required_approvals;
              const href = crDetailHref(namespace, path, cr.number);

              return (
                <tr
                  key={cr.number}
                  className="border-b border-gray-100 dark:border-gray-800"
                >
                  {canBulkReject && (
                    <td className="px-4 py-2.5">
                      <input
                        type="checkbox"
                        className="rounded border-gray-400 dark:border-gray-600"
                        checked={selected.has(cr.number)}
                        disabled={!isOpen}
                        onChange={() => toggleOne(cr.number, isOpen)}
                        aria-label={`Select change request ~${cr.number}`}
                      />
                    </td>
                  )}
                  <td
                    className={cn(
                      "py-2.5 pr-3 font-mono text-xs",
                      !canBulkReject && "pl-4",
                    )}
                  >
                    <Link
                      to={href}
                      className="text-brand-600 hover:underline dark:text-brand-400"
                    >
                      ~{cr.number}
                    </Link>
                  </td>
                  <td className="max-w-[14rem] py-2.5 pr-3">
                    <Link
                      to={href}
                      className="block truncate text-gray-900 hover:text-brand-600 hover:underline dark:text-gray-100 dark:hover:text-brand-400"
                      title={title}
                    >
                      {title}
                    </Link>
                  </td>
                  <td className="max-w-[10rem] truncate py-2.5 pr-3 text-gray-700 dark:text-gray-300">
                    {cr.created_by}
                  </td>
                  <td className="py-2.5 pr-3">
                    <ChangeRequestStatusBadge status={cr.status} />
                  </td>
                  <td className="py-2.5 pr-3">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 font-mono text-xs tabular-nums",
                        approvalsMet
                          ? "font-medium text-green-700 dark:text-green-400"
                          : "text-gray-700 dark:text-gray-300",
                      )}
                    >
                      {approvalsMet && (
                        <Check className="h-3.5 w-3.5 shrink-0" aria-hidden />
                      )}
                      {cr.approval_count}/{cr.required_approvals}
                    </span>
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-xs text-gray-700 dark:text-gray-300">
                    v{cr.base_version}
                    {cr.base_superseded && (
                      <span className="ml-1 text-amber-700 dark:text-amber-400">
                        (superseded)
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-gray-600 dark:text-gray-400">
                    {formatUserDateTime(cr.created_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Modal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title={`Reject ${selectedOpen.length} change request(s)?`}
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setRejectOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="outline-danger"
              size="sm"
              loading={rejectMut.isPending}
              onClick={() =>
                rejectMut.mutate({
                  numbers: selectedOpen,
                  reason: rejectReason,
                })
              }
            >
              Reject
            </Button>
          </>
        }
      >
        <p className="mb-2 text-sm text-gray-600 dark:text-gray-400">
          Optional reason (applied to all selected):
        </p>
        <textarea
          className="w-full rounded border border-gray-300 p-2 text-sm dark:border-gray-600 dark:bg-gray-900"
          rows={3}
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
        />
      </Modal>
    </div>
  );
}
