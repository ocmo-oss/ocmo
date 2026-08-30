import type { AuditEvent } from "../api/types";

export type AuditCategory = "all" | "resolve" | "modifications";

const ENDPOINT_ACTIONS: Array<[RegExp, string]> = [
  [/~config\/~create\//, "Create item"],
  [/~config\/~update\//, "Update item"],
  [/~template\/~create\//, "Create item"],
  [/~template\/~update\//, "Update item"],
  [/~secret\/~create\//, "Create item"],
  [/~secret\/~update\//, "Update item"],
  [/~resolver\/~create\//, "Create item"],
  [/~resolver\/~update\//, "Update item"],
  [/~delete\//, "Delete item"],
  [/~get\//, "read_typed"],
  [/~diff\//, "Diff item"],
  [/~resolve\//, "Resolve"],
  [/~lock\//, "Lock"],
  [/~audit\//, "Audit"],
  [/~navigate\//, "Navigate"],
  [/~search\//, "Search"],
  [/~tag\//, "Set tag"],
  [/~describe\//, "Update description"],
  [/~move\//, "Move item"],
  [/~copy\//, "Copy item"],
  [/~versions\//, "List versions"],
  [/~propagate\//, "Propagate config"],
  [/~download\//, "Download artifact"],
];

function readTyped(objectType?: string | null): string {
  if (objectType) return `Read ${objectType}`;
  return "Read item";
}

/** Fallback for legacy audit rows that predate the persisted operation field. */
export function inferOperationFromLegacyFields(event: AuditEvent): string {
  if (event.event_kind === "resolve_request") return "Resolve";
  if (event.event_kind === "resolve_participant")
    return "Referenced in resolve";

  const endpoint = event.api_endpoint ?? "";
  for (const [pattern, label] of ENDPOINT_ACTIONS) {
    if (!pattern.test(endpoint)) continue;
    if (label === "read_typed") return readTyped(event.object_type);
    if (label === "Set tag" && event.http_method === "DELETE")
      return "Delete tag";
    if (label === "Lock") {
      if (event.http_method === "POST") return "Create lock";
      if (event.http_method === "PUT") return "Update lock";
      if (event.http_method === "DELETE") return "Delete lock";
      return "Read lock";
    }
    return label;
  }

  if (event.http_method === "GET") return readTyped(event.object_type);
  if (event.http_method === "POST") return "Create item";
  if (event.http_method === "PUT" || event.http_method === "PATCH")
    return "Update item";
  if (event.http_method === "DELETE") return "Delete item";
  return event.event_kind;
}

export function formatAuditOperation(event: AuditEvent): string {
  if (event.operation?.trim()) return event.operation;
  return inferOperationFromLegacyFields(event);
}

export function auditCategoryToApiFilter(category: AuditCategory): {
  category?: string;
} {
  if (category === "resolve") return { category: "resolve" };
  if (category === "modifications") return { category: "modifications" };
  return {};
}

export function formatAuditFieldValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}
