import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Columns3, ChevronDown, ChevronUp, Plus, X } from "lucide-react";
import { auditApi } from "../api/audit";
import type { AuditFilters } from "../api/audit";
import type { AuditEvent } from "../api/types";
import { formatUserDateTime } from "../lib/datetime";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import {
  formatAuditFieldValue,
  formatAuditOperation,
  type AuditCategory,
} from "../lib/auditEvent";
import {
  extractAuditEventIdInput,
  applyAuditEventIdFilter,
} from "../lib/auditEventIdSearch";
import {
  AUDIT_COLUMNS,
  auditCellTitle,
  auditFiltersToApi,
  buildAuditSearchParams,
  DEFAULT_AUDIT_COLUMNS,
  MAX_AUDIT_COLUMNS,
  getAuditColumn,
  ITEM_AUDIT_DEFAULT_COLUMNS,
  parseAuditSearchParams,
  renderAuditCell,
  visibleAuditColumns,
  type AuditColumnDef,
  type AuditColumnId,
  type AuditFilterKey,
  type AuditUrlState,
} from "../lib/auditTable";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { Skeleton } from "../components/ui/Skeleton";
import { cn } from "../components/ui/cn";
import { QueryAccessGate } from "../components/QueryAccessGate";

const PAGE_SIZE = 50;
const FILTER_DEBOUNCE_MS = 400;

function patchFilter(
  filters: AuditFilters,
  key: AuditFilterKey,
  value: string,
): AuditFilters {
  const next = { ...filters };
  if (!value) delete next[key];
  else if (key === "permission_ok" || key === "from_cache")
    next[key] = value === "true";
  else if (key === "token_number" || key === "object_version") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) next[key] = parsed;
    else delete next[key];
  } else next[key] = value;
  return next;
}

function filtersKey(filters: AuditFilters): string {
  return JSON.stringify(filters);
}

const CATEGORY_OPTIONS: Array<{ id: AuditCategory; label: string }> = [
  { id: "all", label: "All events" },
  { id: "resolve", label: "Resolve" },
  { id: "modifications", label: "Modifications" },
];

function EventDetailModal({
  event,
  participants,
  participantsLoading,
  onClose,
}: {
  event: AuditEvent;
  participants: AuditEvent[];
  participantsLoading: boolean;
  onClose: () => void;
}) {
  const fields: Array<[string, unknown]> = [
    ["ID", event.id],
    ["Occurred at", formatUserDateTime(event.occurred_at)],
    ["Operation", formatAuditOperation(event)],
    ["Event kind", event.event_kind],
    ["Actor ID", event.auth_id],
    ["Actor email", event.auth_email],
    ["Actor type", event.auth_type],
    ["Token number", event.token_number],
    ["Namespace", event.namespace],
    ["Client IP", event.client_ip],
    ["User agent", event.user_agent],
    ["HTTP method", event.http_method],
    ["API endpoint", event.api_endpoint],
    ["Object type", event.object_type],
    ["Object ID", event.object_id],
    ["Object version", event.object_version],
    ["Subresource type", event.subresource_type],
    ["Subresource", event.subresource],
    ["Resolve type", event.resolve_type],
    ["From cache", event.from_cache],
    ["Parent event ID", event.parent_event_id],
    ["Permission OK", event.permission_ok],
    ["Error", event.error],
  ];

  return (
    <Modal open title="Audit event" onClose={onClose} size="xl">
      <div className="space-y-4 text-sm">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
          {fields.map(([label, value]) => (
            <Fragment key={label}>
              <dt className="font-medium text-gray-500">{label}</dt>
              <dd className="font-mono text-xs break-all text-gray-800 dark:text-gray-200">
                {formatAuditFieldValue(value)}
              </dd>
            </Fragment>
          ))}
        </dl>

        {event.event_kind === "resolve_request" && (
          <div>
            <p className="mb-2 font-medium text-gray-700 dark:text-gray-300">
              Resolve participants
            </p>
            {participantsLoading && (
              <Skeleton lines={3} className="h-8 w-full" />
            )}
            {!participantsLoading && participants.length === 0 && (
              <p className="text-xs text-gray-400">
                No participant rows recorded for this resolve.
              </p>
            )}
            {!participantsLoading && participants.length > 0 && (
              <div className="divide-y rounded border dark:divide-gray-700 dark:border-gray-700">
                {participants.map((participant) => (
                  <div
                    key={participant.id}
                    className="flex flex-wrap items-center gap-2 px-3 py-2 text-xs"
                  >
                    <span className="min-w-0 flex-1 truncate font-mono text-gray-800 dark:text-gray-200">
                      {participant.object_id ?? "—"}
                    </span>
                    <Badge>{participant.object_type ?? "resource"}</Badge>
                    <Badge
                      variant={
                        participant.resolve_type === "direct"
                          ? "info"
                          : "default"
                      }
                    >
                      {participant.resolve_type ?? "—"}
                    </Badge>
                    {participant.object_version != null && (
                      <span className="text-gray-400">
                        v{participant.object_version}
                      </span>
                    )}
                    {participant.from_cache && (
                      <Badge variant="success">cached</Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

function ColumnPickerModal({
  open,
  selected,
  isGlobal,
  onClose,
  onApply,
}: {
  open: boolean;
  selected: AuditColumnId[];
  isGlobal: boolean;
  onClose: () => void;
  onApply: (columns: AuditColumnId[]) => void;
}) {
  const [draft, setDraft] = useState(selected);

  useEffect(() => {
    if (open) setDraft(selected);
  }, [open, selected]);

  const availableColumns = useMemo(
    () => AUDIT_COLUMNS.filter((col) => !col.globalOnly || isGlobal),
    [isGlobal],
  );

  const hiddenColumns = useMemo(
    () => availableColumns.filter((col) => !draft.includes(col.id)),
    [availableColumns, draft],
  );

  const moveColumn = (index: number, direction: -1 | 1) => {
    setDraft((prev) => {
      const target = index + direction;
      if (target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const removeColumn = (id: AuditColumnId) => {
    setDraft((prev) => prev.filter((col) => col !== id));
  };

  const addColumn = (id: AuditColumnId) => {
    setDraft((prev) => {
      if (prev.includes(id) || prev.length >= MAX_AUDIT_COLUMNS) return prev;
      return [...prev, id];
    });
  };

  const atColumnLimit = draft.length >= MAX_AUDIT_COLUMNS;

  return (
    <Modal
      open={open}
      title="Table columns"
      onClose={onClose}
      size="lg"
      footer={
        <>
          <Button
            variant="ghost"
            onClick={() => setDraft([...DEFAULT_AUDIT_COLUMNS])}
          >
            Reset
          </Button>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={draft.length === 0}
            onClick={() => {
              onApply(
                draft.length > 0
                  ? draft.slice(0, MAX_AUDIT_COLUMNS)
                  : [...DEFAULT_AUDIT_COLUMNS],
              );
              onClose();
            }}
          >
            Apply
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <p className="mb-2 text-xs text-gray-500 dark:text-gray-400">
            Order below is left-to-right in the table. Use arrows to reorder. Up
            to {MAX_AUDIT_COLUMNS} columns can be shown at once
            {atColumnLimit
              ? " (limit reached)"
              : ` (${draft.length}/${MAX_AUDIT_COLUMNS})`}
            .
          </p>
          {draft.length === 0 ? (
            <p className="text-sm text-gray-400">No columns selected.</p>
          ) : (
            <ul className="max-h-56 space-y-0.5 overflow-y-auto">
              {draft.map((id, index) => {
                const col = getAuditColumn(id);
                const iconBtnClass = cn(
                  "inline-flex h-6 w-6 shrink-0 items-center justify-center rounded p-0",
                  "text-gray-500 hover:bg-slate-200 disabled:pointer-events-none disabled:opacity-40",
                  "dark:text-gray-400 dark:hover:bg-gray-800",
                );
                return (
                  <li
                    key={id}
                    className="flex items-center gap-0.5 rounded border border-slate-300 px-1 py-0.5 dark:border-gray-700"
                  >
                    <button
                      type="button"
                      className={iconBtnClass}
                      disabled={index === 0}
                      onClick={() => moveColumn(index, -1)}
                      aria-label={`Move ${col.label} up`}
                    >
                      <ChevronUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      className={iconBtnClass}
                      disabled={index === draft.length - 1}
                      onClick={() => moveColumn(index, 1)}
                      aria-label={`Move ${col.label} down`}
                    >
                      <ChevronDown className="h-3.5 w-3.5" />
                    </button>
                    <span className="min-w-0 flex-1 truncate px-1 text-xs text-gray-800 dark:text-gray-200">
                      {col.label}
                    </span>
                    <button
                      type="button"
                      className={iconBtnClass}
                      onClick={() => removeColumn(id)}
                      aria-label={`Remove ${col.label}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {hiddenColumns.length > 0 && (
          <div>
            <p className="mb-2 text-xs text-gray-500 dark:text-gray-400">
              Add column
            </p>
            <div className="flex flex-wrap gap-1.5">
              {hiddenColumns.map((col) => (
                <Button
                  key={col.id}
                  type="button"
                  variant="ghost"
                  size="sm"
                  disabled={atColumnLimit}
                  onClick={() => addColumn(col.id)}
                >
                  <Plus className="h-3.5 w-3.5" />
                  {col.label}
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

const FILTER_INPUT_CLASS = cn(
  "mt-0.5 w-full min-w-0 rounded border border-slate-400 bg-surface-elevated px-1.5 py-0.5 text-[11px] leading-tight shadow-sm",
  "placeholder:text-gray-400 dark:border-gray-600 dark:bg-gray-800 dark:placeholder:text-gray-500",
  "focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500",
);

function ColumnHeaderFilter({
  filterKey,
  filterType,
  filterOptions,
  placeholder,
  value,
  onChange,
}: {
  filterKey: AuditFilterKey;
  filterType?: AuditColumnDef["filterType"];
  filterOptions?: AuditColumnDef["filterOptions"];
  placeholder?: string;
  value: string;
  onChange: (key: AuditFilterKey, value: string) => void;
}) {
  if (filterType === "boolean" || filterType === "select") {
    const options =
      filterType === "boolean"
        ? [
            { value: "", label: "any" },
            { value: "true", label: "true" },
            { value: "false", label: "false" },
          ]
        : [{ value: "", label: "any" }, ...(filterOptions ?? [])];

    return (
      <select
        value={value}
        onChange={(e) => onChange(filterKey, e.target.value)}
        className={FILTER_INPUT_CLASS}
        onClick={(e) => e.stopPropagation()}
      >
        {options.map((option) => (
          <option key={option.value || "__any__"} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  return (
    <input
      type={
        filterType === "datetime"
          ? "datetime-local"
          : filterType === "number"
            ? "number"
            : "text"
      }
      value={value}
      onChange={(e) => onChange(filterKey, e.target.value)}
      placeholder={placeholder}
      className={FILTER_INPUT_CLASS}
      onClick={(e) => e.stopPropagation()}
    />
  );
}

function ColumnHeader({
  col,
  filterValue,
  onFilterChange,
}: {
  col: AuditColumnDef;
  filterValue: (key: AuditFilterKey) => string;
  onFilterChange: (key: AuditFilterKey, value: string) => void;
}) {
  const hasFilter = Boolean(col.filterKey || col.secondaryFilterKey);

  return (
    <th className="bg-surface px-2 py-1.5 text-left align-top font-normal dark:bg-gray-900">
      <div className="text-[10px] font-medium uppercase tracking-wide text-gray-500 whitespace-nowrap">
        {col.label}
      </div>
      {hasFilter && (
        <div className="mt-0.5 space-y-0.5">
          {col.filterKey && (
            <ColumnHeaderFilter
              filterKey={col.filterKey}
              filterType={col.filterType}
              filterOptions={col.filterOptions}
              placeholder={col.filterPlaceholder}
              value={filterValue(col.filterKey)}
              onChange={onFilterChange}
            />
          )}
          {col.secondaryFilterKey && (
            <ColumnHeaderFilter
              filterKey={col.secondaryFilterKey}
              filterType={col.secondaryFilterType}
              filterOptions={col.secondaryFilterOptions}
              placeholder={col.secondaryFilterPlaceholder}
              value={filterValue(col.secondaryFilterKey)}
              onChange={onFilterChange}
            />
          )}
        </div>
      )}
    </th>
  );
}

interface AuditTableScope {
  objectType: string;
  objectId: string;
}

interface AuditTableProps {
  namespace?: string;
  isGlobal?: boolean;
  eventId?: string;
  scope?: AuditTableScope;
}

export function AuditTable({
  namespace,
  isGlobal = false,
  eventId,
  scope,
}: AuditTableProps) {
  const isScoped = Boolean(scope);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [scopedOffset, setScopedOffset] = useState(0);
  const [scopedEventId, setScopedEventId] = useState<string | null>(null);

  const urlState = useMemo(
    () => parseAuditSearchParams(searchParams),
    [searchParams],
  );
  const [draftFilters, setDraftFilters] = useState<AuditFilters>(() =>
    isScoped ? {} : urlState.filters,
  );
  const debouncedFilters = useDebouncedValue(draftFilters, FILTER_DEBOUNCE_MS);

  const effectiveFilters = useMemo(() => {
    if (filtersKey(draftFilters) === filtersKey(debouncedFilters))
      return debouncedFilters;
    // Apply clears immediately; keep debouncing while the user is still typing.
    if (filtersKey(draftFilters) === "{}") return draftFilters;
    return debouncedFilters;
  }, [draftFilters, debouncedFilters]);

  useEffect(() => {
    if (!isScoped) setDraftFilters(urlState.filters);
  }, [isScoped, filtersKey(urlState.filters)]);

  useEffect(() => {
    if (isScoped) return;
    if (filtersKey(debouncedFilters) !== filtersKey(draftFilters)) return;
    setSearchParams(
      (prev) => {
        const state = parseAuditSearchParams(prev);
        if (filtersKey(state.filters) === filtersKey(debouncedFilters))
          return prev;
        return buildAuditSearchParams({
          ...state,
          filters: debouncedFilters,
          offset: 0,
        });
      },
      { replace: true },
    );
  }, [debouncedFilters, draftFilters, isScoped, setSearchParams]);

  const scopedColumns = useMemo(() => ITEM_AUDIT_DEFAULT_COLUMNS, []);
  const visibleColumns = useMemo(
    () =>
      visibleAuditColumns(
        isScoped ? scopedColumns : urlState.columns,
        isGlobal,
      ),
    [isScoped, scopedColumns, urlState.columns, isGlobal],
  );

  const lockedFilters = useMemo<AuditFilters | undefined>(() => {
    if (!scope) return undefined;
    return { object_id: scope.objectId };
  }, [scope]);

  const offset = isScoped ? scopedOffset : urlState.offset;

  const listFilters = useMemo(() => {
    const gatedFilters = applyAuditEventIdFilter(effectiveFilters);
    if (isScoped) {
      return {
        ...gatedFilters,
        ...lockedFilters,
        category: "modifications-and-resolve",
        offset,
      };
    }
    return auditFiltersToApi({ ...urlState, filters: gatedFilters });
  }, [isScoped, effectiveFilters, lockedFilters, offset, urlState]);

  const auditBasePath = isGlobal ? "/audit" : `/ns/${namespace}/audit`;
  const queryString = searchParams.toString();
  const activeEventId = isScoped ? scopedEventId : (eventId ?? null);

  const replaceUrlState = (next: AuditUrlState) => {
    setSearchParams(buildAuditSearchParams(next), { replace: true });
  };

  const openEvent = (event: AuditEvent) => {
    if (isScoped) {
      setScopedEventId(event.id);
      return;
    }
    navigate({
      pathname: `${auditBasePath}/${event.id}`,
      search: queryString,
    });
  };

  const closeEvent = () => {
    if (isScoped) {
      setScopedEventId(null);
      return;
    }
    navigate({
      pathname: auditBasePath,
      search: queryString,
    });
  };

  const setFilterValue = (key: AuditFilterKey, value: string) => {
    setDraftFilters((prev) => patchFilter(prev, key, value));
    if (isScoped) setScopedOffset(0);
  };

  const setCategory = (category: AuditCategory) => {
    replaceUrlState({ ...urlState, category, offset: 0 });
  };

  const clearFilters = () => {
    setDraftFilters({});
    if (isScoped) {
      setScopedOffset(0);
      return;
    }
    replaceUrlState({
      category: "all",
      columns: urlState.columns,
      filters: {},
      offset: 0,
    });
  };

  const setOffset = (nextOffset: number) => {
    if (isScoped) {
      setScopedOffset(nextOffset);
      return;
    }
    replaceUrlState({ ...urlState, offset: nextOffset });
  };

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [
      "audit",
      namespace ?? "global",
      isScoped ? "item" : "page",
      scope?.objectId,
      listFilters,
    ],
    queryFn: ({ signal }) =>
      isGlobal
        ? auditApi.listGlobal({ ...listFilters, limit: PAGE_SIZE }, signal)
        : auditApi.listNamespace(
            namespace!,
            { ...listFilters, limit: PAGE_SIZE },
            signal,
          ),
    enabled: isGlobal || !!namespace,
    staleTime: 15_000,
    placeholderData: keepPreviousData,
  });

  const selectedFromList = activeEventId
    ? data?.items.find((item) => item.id === activeEventId)
    : undefined;

  const { data: fetchedEvent, isLoading: eventLoading } = useQuery({
    queryKey: ["audit-event", namespace ?? "global", activeEventId],
    queryFn: ({ signal }) =>
      isGlobal
        ? auditApi.getGlobalEvent(activeEventId!, signal)
        : auditApi.getEvent(namespace!, activeEventId!, signal),
    enabled: !!activeEventId && !selectedFromList,
    staleTime: 15_000,
  });

  const selectedEvent = activeEventId
    ? (selectedFromList ?? fetchedEvent ?? null)
    : null;

  const { data: participantsData, isLoading: participantsLoading } = useQuery({
    queryKey: ["audit-participants", namespace ?? "global", selectedEvent?.id],
    queryFn: ({ signal }) =>
      isGlobal
        ? auditApi.listGlobal(
            { parent_event_id: selectedEvent!.id, limit: 200 },
            signal,
          )
        : auditApi.listNamespace(
            namespace!,
            { parent_event_id: selectedEvent!.id, limit: 200 },
            signal,
          ),
    enabled: !!selectedEvent && selectedEvent.event_kind === "resolve_request",
    staleTime: 15_000,
  });

  const filterValue = (key: AuditFilterKey): string => {
    const value = draftFilters[key];
    if (value === undefined || value === null) return "";
    return String(value);
  };

  const hasClearableFilters =
    filtersKey(draftFilters) !== "{}" ||
    (!isScoped && urlState.category !== "all");

  return (
    <div className="flex h-full flex-col">
      {!isScoped && (
        <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2 dark:border-gray-700">
          {CATEGORY_OPTIONS.map((option) => (
            <Button
              key={option.id}
              size="sm"
              variant={urlState.category === option.id ? "primary" : "ghost"}
              onClick={() => setCategory(option.id)}
            >
              {option.label}
            </Button>
          ))}
          <div className="ml-auto flex items-center gap-2">
            <label htmlFor="audit-event-id-search" className="sr-only">
              Event ID
            </label>
            <input
              id="audit-event-id-search"
              type="text"
              value={filterValue("event_id")}
              onChange={(e) =>
                setFilterValue(
                  "event_id",
                  extractAuditEventIdInput(e.target.value),
                )
              }
              placeholder="Event ID"
              spellCheck={false}
              className={cn(
                "w-56 rounded border border-slate-400 bg-surface-elevated px-2 py-1 text-xs font-mono shadow-sm",
                "placeholder:font-sans placeholder:text-gray-400",
                "dark:border-gray-600 dark:bg-gray-800 dark:placeholder:text-gray-500",
                "focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500",
              )}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setColumnsOpen(true)}
            >
              <Columns3 className="h-4 w-4" /> Columns
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              disabled={!hasClearableFilters}
            >
              Clear filters
            </Button>
          </div>
        </div>
      )}

      {isScoped && hasClearableFilters && (
        <div className="flex justify-end border-b px-4 py-1.5 dark:border-gray-700">
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        </div>
      )}

      <QueryAccessGate
        isLoading={isLoading}
        isError={isError}
        error={error}
        hasData={!!data}
        permissionDeniedMessage="You do not have permission to view the audit log."
        loadingFallback={
          <div className="space-y-2 p-4">
            {Array.from({ length: 10 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        }
      >
        <div className="flex-1 overflow-auto">
          {data && (
            <table className="w-full table-fixed divide-y divide-slate-200 dark:divide-gray-800">
              <thead className="sticky top-0 z-10 bg-surface dark:bg-gray-900">
                <tr>
                  {visibleColumns.map((col) => (
                    <ColumnHeader
                      key={col.id}
                      col={col}
                      filterValue={filterValue}
                      onFilterChange={setFilterValue}
                    />
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-surface-elevated dark:divide-gray-800/50 dark:bg-gray-900">
                {data.items.map((event) => (
                  <tr
                    key={event.id}
                    className={cn(
                      "cursor-pointer hover:bg-slate-100 dark:hover:bg-gray-800/40",
                      activeEventId === event.id &&
                        "bg-brand-50/50 outline outline-2 outline-offset-[-2px] outline-brand-400 dark:bg-brand-900/20",
                    )}
                    onClick={() => openEvent(event)}
                  >
                    {visibleColumns.map((col) => (
                      <td
                        key={col.id}
                        title={auditCellTitle(col.id, event)}
                        className={cn(
                          "px-2 py-1.5 text-xs truncate",
                          col.id === "operation" ||
                            col.id === "api_endpoint" ||
                            col.id === "user_agent"
                            ? "text-gray-700 dark:text-gray-300"
                            : col.id === "occurred_at"
                              ? "text-gray-400"
                              : "font-mono text-gray-600 dark:text-gray-400",
                        )}
                      >
                        {renderAuditCell(col.id, event)}
                      </td>
                    ))}
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr>
                    <td
                      colSpan={visibleColumns.length || 1}
                      className="px-4 py-12 text-center text-sm text-gray-400"
                    >
                      No audit events found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>

        {data && data.count > 0 && (
          <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-gray-500 dark:border-gray-700">
            <span>
              {data.count} event{data.count === 1 ? "" : "s"}
              {data.count > PAGE_SIZE && (
                <>
                  {" "}
                  · {offset + 1}–{Math.min(offset + PAGE_SIZE, data.count)}
                </>
              )}
            </span>
            {data.count > PAGE_SIZE && (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={offset + PAGE_SIZE >= data.count}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </QueryAccessGate>

      {!isScoped && (
        <ColumnPickerModal
          open={columnsOpen}
          selected={urlState.columns}
          isGlobal={isGlobal}
          onClose={() => setColumnsOpen(false)}
          onApply={(columns) => replaceUrlState({ ...urlState, columns })}
        />
      )}

      {activeEventId && selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          participants={participantsData?.items ?? []}
          participantsLoading={participantsLoading}
          onClose={closeEvent}
        />
      )}

      {activeEventId && !selectedEvent && eventLoading && (
        <Modal open title="Audit event" onClose={closeEvent} size="xl">
          <Skeleton lines={6} className="h-6 w-full" />
        </Modal>
      )}

      {activeEventId && !selectedEvent && !eventLoading && (
        <Modal open title="Audit event" onClose={closeEvent} size="xl">
          <p className="text-sm text-gray-500">Audit event not found.</p>
        </Modal>
      )}
    </div>
  );
}

export function NamespaceAuditPage() {
  const { namespace, eventId } = useParams<{
    namespace: string;
    eventId?: string;
  }>();
  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-4 py-3 dark:border-gray-700">
        <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          Audit log —{" "}
          <span className="font-mono text-brand-600">{namespace}</span>
        </h1>
      </div>
      <div className="flex-1 overflow-hidden">
        <AuditTable namespace={namespace} eventId={eventId} />
      </div>
    </div>
  );
}

export function GlobalAuditPage() {
  const { eventId } = useParams<{ eventId?: string }>();
  return (
    <div className="flex h-full flex-col">
      <div className="border-b px-4 py-3 dark:border-gray-700">
        <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">
          Global audit log
        </h1>
        <p className="text-xs text-gray-400">
          Cross-namespace — global administrators only
        </p>
      </div>
      <div className="flex-1 overflow-hidden">
        <AuditTable isGlobal eventId={eventId} />
      </div>
    </div>
  );
}
