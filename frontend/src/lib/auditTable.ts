import { createElement, type ReactNode } from "react";
import type { AuditFilters } from "../api/audit";
import type { AuditEvent } from "../api/types";
import { formatUserDateTime, formatUserDateTimeRelative } from "./datetime";
import {
  auditCategoryToApiFilter,
  formatAuditFieldValue,
  formatAuditOperation,
  type AuditCategory,
} from "./auditEvent";
import { applyAuditEventIdFilter } from "./auditEventIdSearch";
import { Badge } from "../components/ui/Badge";

export type AuditColumnId =
  | "operation"
  | "occurred_at"
  | "id"
  | "client_ip"
  | "user_agent"
  | "auth_id"
  | "auth_email"
  | "auth_type"
  | "token_number"
  | "namespace"
  | "http_method"
  | "api_endpoint"
  | "object_type"
  | "object_id"
  | "object_version"
  | "subresource_type"
  | "subresource"
  | "permission_ok"
  | "error"
  | "resolve_type"
  | "from_cache"
  | "parent_event_id"
  | "event_kind";

export type AuditFilterKey = keyof AuditFilters;

type FilterInputType = "text" | "boolean" | "datetime" | "number" | "select";

export interface AuditFilterOption {
  value: string;
  label: string;
}

export interface AuditColumnDef {
  id: AuditColumnId;
  label: string;
  filterKey?: AuditFilterKey;
  filterType?: FilterInputType;
  filterPlaceholder?: string;
  filterOptions?: AuditFilterOption[];
  secondaryFilterKey?: AuditFilterKey;
  secondaryFilterType?: FilterInputType;
  secondaryFilterPlaceholder?: string;
  secondaryFilterOptions?: AuditFilterOption[];
  globalOnly?: boolean;
}

export const MAX_AUDIT_COLUMNS = 10;

const AUDIT_AUTH_TYPE_OPTIONS: AuditFilterOption[] = [
  { value: "user", label: "user" },
  { value: "resolver", label: "resolver" },
];

const AUDIT_EVENT_KIND_OPTIONS: AuditFilterOption[] = [
  { value: "operation", label: "operation" },
  { value: "resolve_request", label: "resolve_request" },
  { value: "resolve_participant", label: "resolve_participant" },
];

const AUDIT_OBJECT_TYPE_OPTIONS: AuditFilterOption[] = [
  { value: "config", label: "config" },
  { value: "template", label: "template" },
  { value: "secret", label: "secret" },
  { value: "resolver", label: "resolver" },
  { value: "folder", label: "folder" },
  { value: "namespace", label: "namespace" },
  { value: "lock", label: "lock" },
  { value: "global_permission", label: "global_permission" },
  { value: "artifact", label: "artifact" },
  { value: "propagation", label: "propagation" },
];

const AUDIT_HTTP_METHOD_OPTIONS: AuditFilterOption[] = [
  { value: "GET", label: "GET" },
  { value: "POST", label: "POST" },
  { value: "PUT", label: "PUT" },
  { value: "PATCH", label: "PATCH" },
  { value: "DELETE", label: "DELETE" },
];

const AUDIT_RESOLVE_TYPE_OPTIONS: AuditFilterOption[] = [
  { value: "direct", label: "direct" },
  { value: "nested", label: "nested" },
];

const AUDIT_SUBRESOURCE_TYPE_OPTIONS: AuditFilterOption[] = [
  { value: "tag", label: "tag" },
  { value: "path", label: "path" },
  { value: "token", label: "token" },
  { value: "trigger", label: "trigger" },
  { value: "query", label: "query" },
];

const AUDIT_OPERATION_OPTIONS: AuditFilterOption[] = [
  { value: "Resolve", label: "Resolve" },
  { value: "Referenced in resolve", label: "Referenced in resolve" },
  { value: "Create item", label: "Create item" },
  { value: "Update item", label: "Update item" },
  { value: "Delete item", label: "Delete item" },
  { value: "Set tag", label: "Set tag" },
  { value: "Delete tag", label: "Delete tag" },
  { value: "Diff item", label: "Diff item" },
  { value: "List versions", label: "List versions" },
  { value: "Navigate", label: "Navigate" },
  { value: "Search", label: "Search" },
  { value: "Read lock", label: "Read lock" },
  { value: "Create lock", label: "Create lock" },
  { value: "Update lock", label: "Update lock" },
  { value: "Delete lock", label: "Delete lock" },
  { value: "List locks", label: "List locks" },
  { value: "Propagate config", label: "Propagate config" },
  { value: "Rotate token", label: "Rotate token" },
  { value: "Download artifact", label: "Download artifact" },
  { value: "Update description", label: "Update description" },
  { value: "Promote stable tag", label: "Promote stable tag" },
  { value: "Copy item", label: "Copy item" },
  { value: "Move item", label: "Move item" },
  { value: "Read namespace", label: "Read namespace" },
  { value: "Create namespace", label: "Create namespace" },
  { value: "Update namespace", label: "Update namespace" },
  { value: "Delete namespace", label: "Delete namespace" },
  { value: "List permissions", label: "List permissions" },
  { value: "Read permission", label: "Read permission" },
  { value: "Create permission", label: "Create permission" },
  { value: "Update permission", label: "Update permission" },
  { value: "Delete permission", label: "Delete permission" },
  { value: "Move permission", label: "Move permission" },
  { value: "Read config", label: "Read config" },
  { value: "Read template", label: "Read template" },
  { value: "Read secret", label: "Read secret" },
  { value: "Read resolver", label: "Read resolver" },
  { value: "Read folder", label: "Read folder" },
  { value: "Read item", label: "Read item" },
];

export const AUDIT_COLUMNS: AuditColumnDef[] = [
  {
    id: "occurred_at",
    label: "Time",
    filterKey: "from",
    filterType: "datetime",
    filterPlaceholder: "from",
    secondaryFilterKey: "to",
    secondaryFilterType: "datetime",
    secondaryFilterPlaceholder: "to",
  },
  {
    id: "operation",
    label: "Operation",
    filterKey: "operation",
    filterType: "select",
    filterOptions: AUDIT_OPERATION_OPTIONS,
  },
  {
    id: "auth_email",
    label: "Actor email",
    filterKey: "auth_email",
    filterPlaceholder: "email",
  },
  {
    id: "auth_id",
    label: "Actor ID",
    filterKey: "auth_id",
    filterPlaceholder: "subject",
  },
  {
    id: "auth_type",
    label: "Actor type",
    filterKey: "auth_type",
    filterType: "select",
    filterOptions: AUDIT_AUTH_TYPE_OPTIONS,
  },
  {
    id: "token_number",
    label: "Token #",
    filterKey: "token_number",
    filterType: "number",
  },
  {
    id: "namespace",
    label: "Namespace",
    filterKey: "namespace",
    globalOnly: true,
  },
  {
    id: "event_kind",
    label: "Event kind",
    filterKey: "event_kind",
    filterType: "select",
    filterOptions: AUDIT_EVENT_KIND_OPTIONS,
  },
  {
    id: "object_type",
    label: "Object type",
    filterKey: "object_type",
    filterType: "select",
    filterOptions: AUDIT_OBJECT_TYPE_OPTIONS,
  },
  {
    id: "object_id",
    label: "Object ID",
    filterKey: "object_id",
    filterPlaceholder: "path prefix",
  },
  {
    id: "object_version",
    label: "Object version",
    filterKey: "object_version",
    filterType: "number",
  },
  {
    id: "subresource_type",
    label: "Subresource type",
    filterKey: "subresource_type",
    filterType: "select",
    filterOptions: AUDIT_SUBRESOURCE_TYPE_OPTIONS,
  },
  {
    id: "subresource",
    label: "Subresource",
    filterKey: "subresource",
    filterPlaceholder: "latest",
  },
  {
    id: "http_method",
    label: "HTTP method",
    filterKey: "http_method",
    filterType: "select",
    filterOptions: AUDIT_HTTP_METHOD_OPTIONS,
  },
  {
    id: "api_endpoint",
    label: "API endpoint",
    filterKey: "api_endpoint",
    filterPlaceholder: "/api/v1/...",
  },
  {
    id: "permission_ok",
    label: "Outcome",
    filterKey: "permission_ok",
    filterType: "boolean",
  },
  {
    id: "resolve_type",
    label: "Resolve type",
    filterKey: "resolve_type",
    filterType: "select",
    filterOptions: AUDIT_RESOLVE_TYPE_OPTIONS,
  },
  {
    id: "from_cache",
    label: "From cache",
    filterKey: "from_cache",
    filterType: "boolean",
  },
  {
    id: "parent_event_id",
    label: "Parent event",
    filterKey: "parent_event_id",
    filterPlaceholder: "uuid",
  },
  { id: "client_ip", label: "Client IP", filterKey: "client_ip" },
  { id: "user_agent", label: "User agent", filterKey: "user_agent" },
  { id: "error", label: "Error", filterKey: "error" },
  {
    id: "id",
    label: "Event ID",
    filterKey: "event_id",
    filterPlaceholder: "uuid",
  },
];

export const DEFAULT_AUDIT_COLUMNS: AuditColumnId[] = [
  "occurred_at",
  "auth_email",
  "operation",
  "object_type",
  "object_id",
  "permission_ok",
  "error",
];

export const ITEM_AUDIT_DEFAULT_COLUMNS: AuditColumnId[] = [
  "occurred_at",
  "auth_email",
  "operation",
  "permission_ok",
  "error",
];

const COLUMN_MAP = Object.fromEntries(
  AUDIT_COLUMNS.map((col) => [col.id, col]),
) as Record<AuditColumnId, AuditColumnDef>;

const FILTER_PARAM_KEYS: AuditFilterKey[] = [
  "auth_id",
  "auth_email",
  "auth_type",
  "object_type",
  "object_id",
  "http_method",
  "api_endpoint",
  "permission_ok",
  "resolve_type",
  "from_cache",
  "event_kind",
  "parent_event_id",
  "client_ip",
  "user_agent",
  "token_number",
  "object_version",
  "operation",
  "subresource_type",
  "subresource",
  "event_id",
  "error",
  "namespace",
  "search",
  "from",
  "to",
];

export interface AuditUrlState {
  category: AuditCategory;
  columns: AuditColumnId[];
  filters: AuditFilters;
  offset: number;
}

function parseBoolean(value: string | null): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

function parseNumber(value: string | null): number | undefined {
  if (!value?.trim()) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

export function parseAuditColumns(value: string | null): AuditColumnId[] {
  if (!value?.trim()) return DEFAULT_AUDIT_COLUMNS;
  const ids = value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  const valid = ids.filter((id): id is AuditColumnId => id in COLUMN_MAP);
  const columns = valid.length > 0 ? valid : DEFAULT_AUDIT_COLUMNS;
  return columns.slice(0, MAX_AUDIT_COLUMNS);
}

export function parseAuditSearchParams(params: URLSearchParams): AuditUrlState {
  const category = (params.get("category") as AuditCategory | null) ?? "all";
  const columns = parseAuditColumns(params.get("cols"));
  const filters: AuditFilters = {};

  for (const key of FILTER_PARAM_KEYS) {
    const raw = params.get(key as string);
    if (!raw) continue;
    if (key === "permission_ok" || key === "from_cache") {
      const parsed = parseBoolean(raw);
      if (parsed !== undefined) filters[key] = parsed;
      continue;
    }
    if (key === "token_number" || key === "object_version") {
      const parsed = parseNumber(raw);
      if (parsed !== undefined) filters[key] = parsed;
      continue;
    }
    filters[key] = raw;
  }

  const offset = parseNumber(params.get("offset")) ?? 0;

  return {
    category:
      category === "resolve" || category === "modifications" ? category : "all",
    columns,
    filters,
    offset,
  };
}

export function buildAuditSearchParams(state: AuditUrlState): URLSearchParams {
  const params = new URLSearchParams();
  const filters = applyAuditEventIdFilter(state.filters);

  if (state.category !== "all") params.set("category", state.category);
  if (state.offset > 0) params.set("offset", String(state.offset));

  const defaultCols = DEFAULT_AUDIT_COLUMNS.join(",");
  const cols = state.columns.join(",");
  if (cols !== defaultCols) params.set("cols", cols);

  for (const key of FILTER_PARAM_KEYS) {
    const value = filters[key];
    if (value === undefined || value === "") continue;
    params.set(key as string, String(value));
  }

  return params;
}

export function auditFiltersToApi(state: AuditUrlState): AuditFilters {
  return applyAuditEventIdFilter({
    ...state.filters,
    ...auditCategoryToApiFilter(state.category),
    offset: state.offset,
  });
}

export function getAuditColumn(id: AuditColumnId): AuditColumnDef {
  return COLUMN_MAP[id];
}

export function visibleAuditColumns(
  columns: AuditColumnId[],
  isGlobal: boolean,
): AuditColumnDef[] {
  return columns
    .map((id) => COLUMN_MAP[id])
    .filter((col): col is AuditColumnDef => Boolean(col))
    .filter((col) => !col.globalOnly || isGlobal);
}

function renderPermissionBadge(value: boolean | null | undefined): ReactNode {
  if (value === false)
    return createElement(Badge, { variant: "error", children: "denied" });
  if (value === true)
    return createElement(Badge, { variant: "success", children: "ok" });
  return createElement("span", { className: "text-gray-400" }, "—");
}

export function renderAuditCell(
  columnId: AuditColumnId,
  event: AuditEvent,
): ReactNode {
  switch (columnId) {
    case "operation":
      return formatAuditOperation(event);
    case "occurred_at":
      return formatUserDateTimeRelative(event.occurred_at);
    case "permission_ok":
      return renderPermissionBadge(event.permission_ok);
    case "from_cache":
      return formatAuditFieldValue(event.from_cache);
    case "token_number":
    case "object_version":
      return formatAuditFieldValue(event[columnId]);
    case "namespace":
      return formatAuditFieldValue(event.namespace);
    case "id":
      return event.id;
    default:
      return formatAuditFieldValue(event[columnId as keyof AuditEvent]);
  }
}

export function auditCellTitle(
  columnId: AuditColumnId,
  event: AuditEvent,
): string | undefined {
  if (columnId === "occurred_at") return formatUserDateTime(event.occurred_at);
  if (columnId === "operation") return formatAuditOperation(event);
  const value =
    columnId === "id" ? event.id : event[columnId as keyof AuditEvent];
  const text = formatAuditFieldValue(value);
  return text === "—" ? undefined : text;
}
