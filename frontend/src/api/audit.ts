import { api } from "./client";
import { localDateTimeInputToUtcIso } from "../lib/datetime";
import type {
  AuditEvent,
  AuditTimelineEntry,
  PaginatedResponse,
} from "./types";

export interface ResolveSeriesBucket {
  start: string;
  direct: number;
  nested: number;
  errors: number;
}

export interface ResolveSeriesResponse {
  bucket_seconds: number;
  buckets: ResolveSeriesBucket[];
}

export interface AuditFilters {
  auth_id?: string;
  auth_email?: string;
  auth_type?: string;
  object_type?: string;
  object_id?: string;
  http_method?: string;
  api_endpoint?: string;
  permission_ok?: boolean;
  resolve_type?: string;
  from_cache?: boolean;
  event_kind?: string;
  category?: string;
  parent_event_id?: string;
  client_ip?: string;
  user_agent?: string;
  token_number?: number;
  object_version?: number;
  operation?: string;
  subresource_type?: string;
  subresource?: string;
  event_id?: string;
  error?: string;
  namespace?: string;
  search?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
  [key: string]: string | number | boolean | undefined;
}

function serializeAuditFilters(
  filters?: AuditFilters,
): AuditFilters | undefined {
  if (!filters) return filters;
  const { from, to, ...rest } = filters;
  return {
    ...rest,
    ...(from ? { from: localDateTimeInputToUtcIso(from) ?? from } : {}),
    ...(to ? { to: localDateTimeInputToUtcIso(to) ?? to } : {}),
  };
}

export const auditApi = {
  listGlobal: (filters?: AuditFilters, signal?: AbortSignal) =>
    api.get<PaginatedResponse<AuditEvent>>("/audit/", {
      params: serializeAuditFilters(filters),
      signal,
    }),

  listNamespace: (ns: string, filters?: AuditFilters, signal?: AbortSignal) =>
    api.get<PaginatedResponse<AuditEvent>>(`/ns/${ns}/~audit/`, {
      params: serializeAuditFilters(filters),
      signal,
    }),

  getEvent: (ns: string, eventId: string, signal?: AbortSignal) =>
    api.get<AuditEvent>(`/ns/${ns}/~audit/${eventId}`, { signal }),

  getGlobalEvent: (eventId: string, signal?: AbortSignal) =>
    api.get<AuditEvent>(`/audit/${eventId}`, { signal }),

  getResolveSeries: (
    ns: string,
    params: {
      object_id: string;
      object_type: string;
      from: string;
      to: string;
      bucket_seconds: number;
    },
    signal?: AbortSignal,
  ) =>
    api.get<ResolveSeriesResponse>(`/ns/${ns}/~audit/resolve-series/`, {
      params,
      signal,
    }),

  listItemTimeline: (
    ns: string,
    params: {
      object_id: string;
      object_type: string;
      search?: string;
      limit?: number;
      offset?: number;
    },
    signal?: AbortSignal,
  ) =>
    api.get<PaginatedResponse<AuditTimelineEntry>>(
      `/ns/${ns}/~audit/timeline/`,
      { params, signal },
    ),
};
