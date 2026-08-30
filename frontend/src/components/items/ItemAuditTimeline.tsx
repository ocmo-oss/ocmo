import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { auditApi } from "../../api/audit";
import type { ItemType } from "../../api/types";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import {
  formatUserDateTimeRelative,
  formatUserDateTimeShort,
} from "../../lib/datetime";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Skeleton } from "../ui/Skeleton";
import { AuditTimelineMessage } from "./AuditTimelineMessage";

const PAGE_SIZE = 10;
const SEARCH_DEBOUNCE_MS = 300;

interface ItemAuditTimelineProps {
  namespace: string;
  path: string;
  type: ItemType;
}

export function ItemAuditTimeline({
  namespace,
  path,
  type,
}: ItemAuditTimelineProps) {
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const debouncedSearch = useDebouncedValue(search, SEARCH_DEBOUNCE_MS);

  const { data, isLoading, isError } = useQuery({
    queryKey: [
      "audit-timeline",
      namespace,
      type,
      path,
      debouncedSearch,
      offset,
    ],
    queryFn: ({ signal }) =>
      auditApi.listItemTimeline(
        namespace,
        {
          object_id: path,
          object_type: type,
          search: debouncedSearch || undefined,
          limit: PAGE_SIZE,
          offset,
        },
        signal,
      ),
    staleTime: 15_000,
    refetchOnMount: "always",
    placeholderData: keepPreviousData,
  });

  const onSearchChange = (value: string) => {
    setSearch(value);
    setOffset(0);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-3 border-b px-3 py-2 dark:border-gray-700">
        <h2 className="shrink-0 text-xs font-medium text-gray-700 dark:text-gray-300">
          Modifications history
        </h2>
        <div className="relative ml-auto w-full max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <Input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search audit notes…"
            className="h-7 py-1 pl-8 text-xs"
            aria-label="Search audit notes"
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
        {isLoading && !data ? (
          <Skeleton lines={6} className="h-7 w-full" />
        ) : isError ? (
          <p className="py-6 text-center text-xs text-red-500">
            Failed to load audit timeline
          </p>
        ) : data && data.items.length > 0 ? (
          <ol className="relative space-y-0">
            {data.items.map((entry, index) => (
              <li key={entry.id} className="relative flex gap-2 pb-3 last:pb-0">
                {index < data.items.length - 1 && (
                  <span
                    aria-hidden
                    className="absolute left-[5px] top-3 h-[calc(100%-0.25rem)] w-px bg-slate-300 dark:bg-gray-700"
                  />
                )}
                <span
                  aria-hidden
                  className="relative z-10 mt-1 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-slate-400 bg-surface-elevated dark:border-gray-600 dark:bg-gray-900"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-xs leading-snug text-gray-800 dark:text-gray-200">
                    <AuditTimelineMessage entry={entry} />
                  </p>
                  <p
                    className="mt-0.5 text-[11px] text-gray-400"
                    title={formatUserDateTimeShort(entry.occurred_at)}
                  >
                    {formatUserDateTimeRelative(entry.occurred_at)}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="py-8 text-center text-xs text-gray-400">
            No audit events found
          </p>
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
    </div>
  );
}
