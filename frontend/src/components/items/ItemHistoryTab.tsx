import { useMemo, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { createPatch } from "diff";
import { formatUserDateTime } from "../../lib/datetime";
import { GitCompare, Plus, Search } from "lucide-react";
import { treeApi } from "../../api/tree";
import type { ItemType } from "../../api/types";
import { useItemVersion } from "../../hooks/useItemVersion";
import type { HistorySelectionItem } from "../../hooks/useHistorySelection";
import { Badge } from "../ui/Badge";
import { TagBadge } from "../../lib/itemBadges";
import { Button } from "../ui/Button";
import { Skeleton } from "../ui/Skeleton";
import { invalidateItemDetailQueries } from "../../lib/treeQuery";
import { pushApiError } from "../../store/notifications";
import { showToast } from "../ui/Toast";
import { useReservedTags } from "../../store/health";
import {
  isReservedTagName,
  reservedTagsForItemType,
} from "../../store/versionBootstrap";
import { cn } from "../ui/cn";
import { ArrowLeftRight } from "lucide-react";

const PAGE_SIZE = 20;

interface ItemHistoryTabProps {
  namespace: string;
  path: string;
  itemType: ItemType;
  currentVersion: number;
  canTag: boolean;
  isSelected: (key: string) => boolean;
  onToggle: (item: HistorySelectionItem) => void;
  onDiffWithCurrent: (otherRef: string) => void;
  diffPair: { from: string; to: string } | null;
  onCloseDiff: () => void;
  onSwapDiff: () => void;
}

function renderUnifiedDiff(from: string, to: string, fileName: string) {
  const patch =
    from === to ? "No differences\n" : createPatch(fileName, from, to);
  const lines = patch.split("\n");

  return (
    <pre className="min-h-0 flex-1 overflow-auto rounded bg-gray-950 p-4 text-xs font-mono text-gray-200">
      {lines.map((line, i) => {
        let cls = "text-gray-400";
        if (line.startsWith("+") && !line.startsWith("+++"))
          cls = "text-green-400";
        else if (line.startsWith("-") && !line.startsWith("---"))
          cls = "text-red-400";
        else if (line.startsWith("@")) cls = "text-blue-400";
        return (
          <span key={i} className={`${cls} block whitespace-pre-wrap`}>
            {line}
          </span>
        );
      })}
    </pre>
  );
}

function SelectionCheckbox({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
}) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      onClick={(e) => e.stopPropagation()}
      aria-label={label}
      className="mt-0.5 shrink-0 rounded border-slate-400 text-brand-600 focus:ring-brand-500 dark:border-gray-600"
    />
  );
}

function InlineTagForm({
  version,
  itemType,
  onCancel,
  onSave,
  saving,
}: {
  version: number;
  itemType: ItemType;
  onCancel: () => void;
  onSave: (tag: string) => void;
  saving: boolean;
}) {
  const [tagName, setTagName] = useState("");
  const reservedTags = useReservedTags();

  const trimmedTag = tagName.trim();
  const reserved = isReservedTagName(trimmedTag, reservedTags, itemType);
  const canSubmit = Boolean(trimmedTag) && !reserved;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || saving) return;
    onSave(trimmedTag);
  };

  return (
    <form
      className="mt-2 flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
      onSubmit={handleSubmit}
    >
      <input
        type="text"
        value={tagName}
        onChange={(e) => setTagName(e.target.value)}
        placeholder="Tag name"
        className="min-w-0 flex-1 rounded border border-slate-300 bg-surface-elevated px-2 py-1 font-mono text-xs dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
        autoFocus
      />
      <Button
        type="submit"
        variant="primary"
        size="sm"
        loading={saving}
        disabled={!canSubmit}
      >
        Save
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
        Cancel
      </Button>
      {reserved && (
        <span className="text-[10px] text-red-500">
          Reserved ({reservedTagsForItemType(reservedTags, itemType).join(", ")}
          )
        </span>
      )}
      <span className="text-[10px] text-gray-400">v{version}</span>
    </form>
  );
}

function ColumnHeader({ title }: { title: string }) {
  return (
    <p className="sticky top-0 z-10 border-b bg-surface-elevated px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:border-gray-700 dark:bg-gray-950">
      {title}
    </p>
  );
}

export function ItemHistoryTab({
  namespace,
  path,
  itemType,
  currentVersion,
  canTag,
  isSelected,
  onToggle,
  onDiffWithCurrent,
  diffPair,
  onCloseDiff,
  onSwapDiff,
}: ItemHistoryTabProps) {
  const qc = useQueryClient();
  const { versionRef, setVersionRef } = useItemVersion();
  const [query, setQuery] = useState("");
  const [taggingVersion, setTaggingVersion] = useState<number | null>(null);

  const tagMut = useMutation({
    mutationFn: ({ tag, version }: { tag: string; version: number }) =>
      treeApi.setTag(namespace, path, { tag, version }),
    onSuccess: () => {
      invalidateItemDetailQueries(qc, namespace, path);
      showToast("Tag saved");
      setTaggingVersion(null);
    },
    onError: (e: Error) => pushApiError("Failed to set tag", e),
  });

  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useInfiniteQuery({
      queryKey: ["versions", namespace, path, "history"],
      queryFn: ({ pageParam = 0, signal }) =>
        treeApi.versions(
          namespace,
          path,
          { limit: PAGE_SIZE, offset: pageParam },
          signal,
        ),
      initialPageParam: 0,
      getNextPageParam: (lastPage, pages) => {
        const loaded = pages.reduce(
          (sum, page) => sum + page.versions.length,
          0,
        );
        return loaded < lastPage.count ? loaded : undefined;
      },
      staleTime: 30_000,
      refetchOnMount: "always",
    });

  const versions = useMemo(
    () => data?.pages.flatMap((page) => page.versions) ?? [],
    [data],
  );

  const tags = data?.pages[0]?.tags ?? [];
  const normalizedQuery = query.trim().toLowerCase();

  const filteredTags = useMemo(() => {
    if (!normalizedQuery) return tags;
    return tags.filter(
      (t) =>
        t.name.toLowerCase().includes(normalizedQuery) ||
        String(t.version).includes(normalizedQuery),
    );
  }, [tags, normalizedQuery]);

  const filteredVersions = useMemo(() => {
    if (!normalizedQuery) return versions;
    return versions.filter(
      (v) =>
        String(v.version).includes(normalizedQuery) ||
        v.tags.some((t) => t.toLowerCase().includes(normalizedQuery)) ||
        v.updater.toLowerCase().includes(normalizedQuery),
    );
  }, [versions, normalizedQuery]);

  const { data: diffData, isLoading: diffLoading } = useQuery({
    queryKey: ["diff", namespace, path, diffPair?.from, diffPair?.to],
    queryFn: ({ signal }) =>
      treeApi.diff(
        namespace,
        path,
        {
          from: diffPair!.from,
          to: diffPair!.to,
        },
        signal,
      ),
    enabled: diffPair !== null,
    staleTime: 0,
  });

  const toggleTag = (tag: { name: string; version: number }) => {
    onToggle({
      key: `tag:${tag.name}`,
      kind: "tag",
      label: tag.name,
      version: tag.version,
      tagName: tag.name,
    });
  };

  const toggleVersion = (version: number) => {
    onToggle({
      key: `v:${version}`,
      kind: "version",
      label: `v${version}`,
      version,
    });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      {!diffPair && (
        <div className="border-b px-4 py-3 dark:border-gray-700">
          <div className="relative max-w-md">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search tags and versions…"
              className="w-full rounded-md border border-slate-300 bg-surface-elevated py-1.5 pl-8 pr-2 text-sm text-gray-800 placeholder-gray-400 focus:border-brand-400 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
        </div>
      )}

      <div
        className={cn(
          "flex min-h-0 overflow-hidden",
          diffPair ? "hidden" : "flex-1",
        )}
      >
        <div className="flex w-1/2 min-w-0 flex-col overflow-hidden border-r dark:border-gray-700">
          <ColumnHeader title="Tags" />
          <div className="flex-1 overflow-y-auto">
            {filteredTags.length === 0 && !isLoading && (
              <p className="px-3 py-4 text-xs text-gray-400">No tags</p>
            )}
            <div className="divide-y dark:divide-gray-700">
              {filteredTags.map((tag) => {
                const key = `tag:${tag.name}`;
                return (
                  <div
                    key={tag.name}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2",
                      isSelected(key) && "bg-brand-50 dark:bg-brand-900/20",
                    )}
                  >
                    <SelectionCheckbox
                      checked={isSelected(key)}
                      onChange={() => toggleTag(tag)}
                      label={`Select tag ${tag.name}`}
                    />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setVersionRef(tag.name);
                      }}
                      className="shrink-0 hover:opacity-80"
                    >
                      <TagBadge
                        name={tag.name}
                        className="text-xs px-2 py-0.5"
                      />
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleTag(tag)}
                      className="min-w-0 flex-1 text-left text-xs text-gray-400 hover:text-gray-500"
                    >
                      v{tag.version}
                    </button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDiffWithCurrent(tag.name)}
                      title="Compare with current"
                    >
                      <GitCompare className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="flex w-1/2 min-w-0 flex-col overflow-hidden">
          <ColumnHeader title="Versions" />
          <div className="flex-1 overflow-y-auto">
            {isLoading && <Skeleton lines={5} className="m-3 h-8 w-full" />}

            {!isLoading && filteredVersions.length === 0 && (
              <p className="px-3 py-4 text-xs text-gray-400">No versions</p>
            )}

            <div className="divide-y dark:divide-gray-700">
              {filteredVersions.map((version) => {
                const versionKey = `v:${version.version}`;
                const isCurrent =
                  versionRef === String(version.version) ||
                  (!versionRef && version.version === currentVersion);

                return (
                  <div
                    key={version.version}
                    className={cn(
                      "px-3 py-2",
                      isCurrent && "bg-brand-50 dark:bg-brand-900/20",
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <SelectionCheckbox
                        checked={isSelected(versionKey)}
                        onChange={() => toggleVersion(version.version)}
                        label={`Select version ${version.version}`}
                      />
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setVersionRef(String(version.version));
                        }}
                        className="shrink-0 font-mono text-sm hover:text-brand-600 dark:hover:text-brand-400"
                      >
                        v{version.version}
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleVersion(version.version)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          {version.tags.map((tag) => (
                            <button
                              key={tag}
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setVersionRef(tag);
                              }}
                              className="inline-flex"
                            >
                              <TagBadge
                                name={tag}
                                className="text-xs px-2 py-0.5"
                              />
                            </button>
                          ))}
                          {version.deleted_at && (
                            <Badge variant="error">deleted</Badge>
                          )}
                        </div>
                        <p className="mt-1 text-xs text-gray-400">
                          {version.updater} ·{" "}
                          {formatUserDateTime(version.created_at)}
                        </p>
                      </button>
                      <div className="flex shrink-0 items-center gap-0.5">
                        {canTag && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              setTaggingVersion((v) =>
                                v === version.version ? null : version.version,
                              );
                            }}
                            title="Add tag"
                          >
                            <Plus className="h-3.5 w-3.5" />
                            Tag
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            onDiffWithCurrent(String(version.version))
                          }
                          title="Compare with current"
                        >
                          <GitCompare className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                    {taggingVersion === version.version && (
                      <InlineTagForm
                        version={version.version}
                        itemType={itemType}
                        saving={tagMut.isPending}
                        onCancel={() => setTaggingVersion(null)}
                        onSave={(tag) =>
                          tagMut.mutate({ tag, version: version.version })
                        }
                      />
                    )}
                  </div>
                );
              })}
            </div>

            {hasNextPage && (
              <div className="p-3">
                <Button
                  variant="secondary"
                  size="sm"
                  loading={isFetchingNextPage}
                  onClick={() => void fetchNextPage()}
                >
                  Load more
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {diffPair && (
        <div className="flex min-h-0 flex-1 flex-col border-t dark:border-gray-700">
          <div className="flex shrink-0 items-center justify-between px-4 py-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Diff: {diffPair.from} → {diffPair.to}
            </p>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={onSwapDiff}
                title="Swap versions"
              >
                <ArrowLeftRight className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" onClick={onCloseDiff}>
                Close
              </Button>
            </div>
          </div>
          {diffLoading && (
            <Skeleton className="mx-4 mb-4 h-32 w-full shrink-0" />
          )}
          {diffData &&
            renderUnifiedDiff(
              diffData.from.content ?? "",
              diffData.to.content ?? "",
              path,
            )}
        </div>
      )}
    </div>
  );
}
