import type { ChangeRequest, ChangeRequestComment } from "../api/types";

export type ChangeRequestActivityItem = {
  id: string;
  created_at: string;
  message: string;
};

function resourceLabel(nodeType: ChangeRequest["node_type"]): string {
  if (nodeType === "template") return "template";
  if (nodeType === "secret") return "secret";
  return "config";
}

function rejectMessage(cr: ChangeRequest): string {
  const resource = resourceLabel(cr.node_type);
  if (cr.rejected_reason === "new_version_published") {
    return `Change request was rejected since a newer version of the ${resource} was published.`;
  }
  const rejector =
    cr.rejected_by && cr.rejected_by !== "system" ? cr.rejected_by : null;
  const base = rejector
    ? `Change request was rejected by ${rejector}.`
    : "Change request was rejected.";
  const reason = cr.rejected_reason?.trim();
  if (reason) {
    return `${base} Reason: ${reason}`;
  }
  return base;
}

/** System timeline entries for the discussion section (approvals, apply, reject, withdraw). */
export function buildChangeRequestActivity(
  cr: ChangeRequest,
): ChangeRequestActivityItem[] {
  const items: ChangeRequestActivityItem[] = [];

  for (const event of cr.approval_events ?? []) {
    items.push({
      id: `approval-${event.approver}-${event.created_at}`,
      created_at: event.created_at,
      message: `${event.approver} approved this change request.`,
    });
  }

  if (cr.applied_at) {
    const version =
      cr.applied_version != null ? ` as version ${cr.applied_version}` : "";
    const by = cr.applied_by ? ` by ${cr.applied_by}` : "";
    items.push({
      id: `applied-${cr.applied_at}`,
      created_at: cr.applied_at,
      message: `Change request was applied${version}${by}.`,
    });
  }

  if (cr.rejected_at) {
    items.push({
      id: `rejected-${cr.rejected_at}`,
      created_at: cr.rejected_at,
      message: rejectMessage(cr),
    });
  }

  if (cr.status === "withdrawn") {
    items.push({
      id: `withdrawn-${cr.updated_at}`,
      created_at: cr.updated_at,
      message: `Change request was withdrawn by ${cr.created_by}.`,
    });
  }

  return items;
}

export type DiscussionTimelineEntry =
  | {
      kind: "comment";
      id: number;
      created_at: string;
      comment: ChangeRequestComment;
    }
  | { kind: "activity"; id: string; created_at: string; message: string };

export function mergeDiscussionTimeline(
  comments: ChangeRequestComment[],
  cr: ChangeRequest,
): DiscussionTimelineEntry[] {
  const activities = buildChangeRequestActivity(cr);
  const entries: DiscussionTimelineEntry[] = [
    ...comments.map((c) => ({
      kind: "comment" as const,
      id: c.id,
      created_at: c.created_at,
      comment: c,
    })),
    ...activities.map((a) => ({
      kind: "activity" as const,
      id: a.id,
      created_at: a.created_at,
      message: a.message,
    })),
  ];
  entries.sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  return entries;
}
