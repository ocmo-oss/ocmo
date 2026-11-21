import { useEffect, useRef } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import type {
  ChangeRequest,
  ChangeRequestComment,
  ChangeRequestStatus,
} from "../api/types";
import { useDocumentPageActive } from "../hooks/useDocumentPageActive";

/** How often open change request pages poll for remote updates. */
export const CHANGE_REQUEST_POLL_MS = 15_000;

export function changeRequestPollInterval(
  status: ChangeRequestStatus | undefined,
): number | false {
  return status === "open" ? CHANGE_REQUEST_POLL_MS : false;
}

export function changeRequestRefetchInterval(
  status: ChangeRequestStatus | undefined,
  pageActive: boolean,
): number | false {
  if (!pageActive) return false;
  return changeRequestPollInterval(status);
}

export function invalidateChangeRequestPageQueries(
  qc: QueryClient,
  namespace: string,
  path: string,
  number: number,
): void {
  void qc.invalidateQueries({
    queryKey: ["change-request", namespace, path, number],
  });
  void qc.invalidateQueries({
    queryKey: ["change-request-comments", namespace, path, number],
  });
  void qc.invalidateQueries({
    queryKey: ["change-request-diff", namespace, path, number],
  });
}

/** Poll only while tab is visible; refetch CR, comments, and diff when tab becomes active again. */
export function useChangeRequestPageSync(
  namespace: string,
  path: string,
  number: number,
): { pageActive: boolean } {
  const qc = useQueryClient();
  const pageActive = useDocumentPageActive();
  const prevPageActive = useRef(pageActive);

  useEffect(() => {
    const becameActive = pageActive && !prevPageActive.current;
    prevPageActive.current = pageActive;
    if (!becameActive || !namespace || !path || number <= 0) return;
    invalidateChangeRequestPageQueries(qc, namespace, path, number);
  }, [pageActive, namespace, path, number, qc]);

  return { pageActive };
}

export function changeRequestDataFingerprint(cr: ChangeRequest): string {
  return JSON.stringify({
    updated_at: cr.updated_at,
    status: cr.status,
    title: cr.title,
    description: cr.description,
    content: cr.content ?? "",
    base_version: cr.base_version,
    base_superseded: cr.base_superseded,
    latest_version: cr.latest_version,
    approval_count: cr.approval_count,
    required_approvals: cr.required_approvals,
    approvers: cr.approvers,
    approval_events: cr.approval_events,
    can_apply: cr.can_apply,
    can_approve: cr.can_approve,
    can_unapprove: cr.can_unapprove,
    applied_version: cr.applied_version,
    applied_by: cr.applied_by,
    applied_at: cr.applied_at,
    rejected_reason: cr.rejected_reason,
    rejected_by: cr.rejected_by,
    rejected_at: cr.rejected_at,
    issues: cr.issues ?? [],
    has_cr_references: cr.has_cr_references,
    referenced_by: cr.referenced_by,
    depends_on: cr.depends_on,
  });
}

export function changeRequestCommentsFingerprint(
  items: Pick<ChangeRequestComment, "id" | "created_at" | "body">[],
  total: number,
): string {
  return JSON.stringify({
    total,
    items: items.map((c) => [c.id, c.created_at, c.body]),
  });
}
