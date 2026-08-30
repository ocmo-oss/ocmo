import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, GitCompare } from "lucide-react";
import { treeApi } from "../api/tree";
import type { ItemType } from "../api/types";
import { DiffSidePicker } from "../components/diff/DiffSidePicker";
import { ApiUnavailable } from "../components/ApiUnavailable";
import { hasDiffVersionHistory, isDiffableType } from "../lib/diffableTypes";
import { isApiUnavailableError } from "../lib/apiAvailability";
import {
  buildCrossConfigDiffSearchParams,
  crossConfigDiffSearchParamsEqual,
  parseCrossConfigDiffSearchParams,
} from "../lib/crossConfigDiffUrl";
import { ITEM_TYPE_LABELS } from "../lib/itemTypes";
import { renderUnifiedDiff } from "../lib/unifiedDiff";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";

function readInitialDiffState() {
  return parseCrossConfigDiffSearchParams(
    new URLSearchParams(window.location.search),
  );
}

export function CrossConfigDiffPage() {
  const { namespace } = useParams<{ namespace: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialState = readInitialDiffState();
  const isApplyingUrlRef = useRef(false);

  const [fromPath, setFromPath] = useState(initialState.fromPath);
  const [toPath, setToPath] = useState(initialState.toPath);
  const [fromType, setFromType] = useState<ItemType | null>(null);
  const [toType, setToType] = useState<ItemType | null>(null);
  const [fromRef, setFromRef] = useState(initialState.fromRef);
  const [toRef, setToRef] = useState(initialState.toRef);
  const [reveal, setReveal] = useState(initialState.reveal);

  const trimmedFrom = fromPath.trim();
  const trimmedTo = toPath.trim();

  const fromItem = useQuery({
    queryKey: ["item", namespace, trimmedFrom, "diff-side"],
    queryFn: ({ signal }) => treeApi.get(namespace!, trimmedFrom, {}, signal),
    enabled: Boolean(namespace && trimmedFrom),
    staleTime: 30_000,
  });

  const toItem = useQuery({
    queryKey: ["item", namespace, trimmedTo, "diff-side"],
    queryFn: ({ signal }) => treeApi.get(namespace!, trimmedTo, {}, signal),
    enabled: Boolean(namespace && trimmedTo),
    staleTime: 30_000,
  });

  const fromResolved =
    !trimmedFrom ||
    (!fromItem.isFetching && (fromItem.data !== undefined || fromItem.isError));
  const toResolved =
    !trimmedTo ||
    (!toItem.isFetching && (toItem.data !== undefined || toItem.isError));
  const sidesResolved = fromResolved && toResolved;

  const canCompare = Boolean(
    trimmedFrom &&
    trimmedTo &&
    fromItem.data &&
    toItem.data &&
    fromItem.data.type === toItem.data.type &&
    isDiffableType(fromItem.data.type),
  );

  const { data, isFetching, isError, error } = useQuery({
    queryKey: [
      "cross-diff",
      namespace,
      trimmedFrom,
      fromRef,
      trimmedTo,
      toRef,
      reveal,
    ],
    queryFn: ({ signal }) =>
      treeApi.diff(
        namespace!,
        trimmedFrom,
        {
          from: fromRef,
          to: toRef,
          to_path: trimmedTo !== trimmedFrom ? trimmedTo : undefined,
          reveal,
        },
        signal,
      ),
    enabled: canCompare,
    staleTime: 0,
    retry: false,
  });

  const handleSwap = () => {
    setFromPath(toPath);
    setToPath(fromPath);
    setFromType(toType);
    setToType(fromType);
    setFromRef(toRef);
    setToRef(fromRef);
  };

  const diffLabel = canCompare
    ? hasDiffVersionHistory(fromItem.data!.type)
      ? `${trimmedFrom}@${fromRef} → ${trimmedTo}@${toRef}`
      : `${trimmedFrom} → ${trimmedTo}`
    : "";

  const typeMismatchHint =
    trimmedFrom &&
    trimmedTo &&
    sidesResolved &&
    fromItem.data &&
    toItem.data &&
    fromItem.data.type !== toItem.data.type
      ? `Both sides must be the same type (from: ${ITEM_TYPE_LABELS[fromItem.data.type]}, to: ${ITEM_TYPE_LABELS[toItem.data.type]}).`
      : null;

  const showRevealSecrets =
    fromType === "secret" ||
    toType === "secret" ||
    fromItem.data?.type === "secret" ||
    toItem.data?.type === "secret";

  const searchParamsKey = searchParams.toString();

  useEffect(() => {
    if (!sidesResolved) return;
    const hasSecret =
      fromItem.data?.type === "secret" || toItem.data?.type === "secret";
    if (!hasSecret) setReveal(false);
  }, [fromItem.data, sidesResolved, toItem.data]);

  useEffect(() => {
    const parsed = parseCrossConfigDiffSearchParams(searchParams);
    const built = canCompare
      ? buildCrossConfigDiffSearchParams({
          fromPath: trimmedFrom,
          toPath: trimmedTo,
          fromRef,
          toRef,
          reveal,
        })
      : new URLSearchParams();

    if (canCompare && crossConfigDiffSearchParamsEqual(searchParams, built))
      return;
    if (!canCompare && searchParamsKey === "") return;

    isApplyingUrlRef.current = true;
    setFromPath(parsed.fromPath);
    setToPath(parsed.toPath);
    setFromRef(parsed.fromRef);
    setToRef(parsed.toRef);
    setReveal(parsed.reveal);
  }, [searchParamsKey]);

  useEffect(() => {
    if (!sidesResolved) return;
    if (isApplyingUrlRef.current) {
      isApplyingUrlRef.current = false;
      return;
    }

    if (canCompare) {
      const next = buildCrossConfigDiffSearchParams({
        fromPath: trimmedFrom,
        toPath: trimmedTo,
        fromRef,
        toRef,
        reveal,
      });
      if (!crossConfigDiffSearchParamsEqual(searchParams, next)) {
        setSearchParams(next, { replace: true });
      }
      return;
    }

    if (searchParamsKey !== "") {
      setSearchParams({}, { replace: true });
    }
  }, [
    canCompare,
    fromRef,
    reveal,
    searchParamsKey,
    setSearchParams,
    sidesResolved,
    toRef,
    trimmedFrom,
    trimmedTo,
  ]);

  return (
    <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden lg:flex-row">
      <aside className="w-full shrink-0 space-y-3 overflow-y-auto border-b border-slate-300 p-4 dark:border-gray-700 lg:w-96 lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-2">
          <GitCompare className="h-5 w-5 shrink-0 text-gray-500" />
          <div className="min-w-0">
            <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Cross-config diff
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Compare configs, templates, secrets, or resolvers at different
              paths or versions.
            </p>
          </div>
        </div>

        <DiffSidePicker
          namespace={namespace!}
          label="From"
          path={fromPath}
          itemType={fromType}
          onPathChange={setFromPath}
          onItemTypeChange={setFromType}
          versionRef={fromRef}
          onVersionRefChange={setFromRef}
          compact
        />

        <div className="flex justify-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSwap}
            title="Swap from and to"
            aria-label="Swap from and to"
          >
            <ArrowLeftRight className="h-4 w-4" />
          </Button>
        </div>

        <DiffSidePicker
          namespace={namespace!}
          label="To"
          path={toPath}
          itemType={toType}
          onPathChange={setToPath}
          onItemTypeChange={setToType}
          versionRef={toRef}
          onVersionRefChange={setToRef}
          compact
        />

        {showRevealSecrets && (
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={reveal}
              onChange={(e) => setReveal(e.target.checked)}
              className="rounded border-slate-400"
            />
            Reveal secrets
          </label>
        )}

        {typeMismatchHint && (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            {typeMismatchHint}
          </p>
        )}
      </aside>

      <section className="flex min-h-[40vh] min-w-0 flex-1 flex-col overflow-hidden p-4 lg:min-h-0">
        <div className="mb-2 flex min-h-[1.25rem] shrink-0 flex-wrap items-center gap-2">
          {canCompare && diffLabel && (
            <p className="truncate text-sm font-medium text-gray-700 dark:text-gray-300">
              {diffLabel}
            </p>
          )}
          {data?.from.decryption_required && (
            <span className="text-xs text-yellow-600 dark:text-yellow-400">
              Secret content hidden — enable reveal to diff values
            </span>
          )}
        </div>

        <div className="flex min-h-0 w-full flex-1 flex-col overflow-hidden rounded-md border border-slate-300 dark:border-gray-700">
          {canCompare && isFetching && (
            <Skeleton className="h-full w-full rounded-none" />
          )}

          {isError && canCompare && !isFetching && (
            <div className="flex h-full items-center justify-center p-6">
              {isApiUnavailableError(error) ? (
                <ApiUnavailable
                  message={error instanceof Error ? error.message : undefined}
                />
              ) : (
                <p className="text-sm text-red-500">
                  {(error as Error).message}
                </p>
              )}
            </div>
          )}

          {data && !isFetching && canCompare && (
            <div className="h-full min-h-0 w-full">
              {renderUnifiedDiff(
                data.from.content ?? "",
                data.to.content ?? "",
                `${data.from.path} ↔ ${data.to.path}`,
              )}
            </div>
          )}

          {!canCompare && (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm text-gray-400">
              Select two matching items to view the diff
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
