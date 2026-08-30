import { useLayoutEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronUp,
  Maximize2,
  Pencil,
  Save,
  X,
} from "lucide-react";
import { treeApi } from "../../api/tree";
import { Button } from "../ui/Button";
import { MarkdownEditor } from "../ui/MarkdownEditor";
import { DescriptionMarkdown } from "../ui/DescriptionMarkdown";
import { DescriptionReadModal } from "./DescriptionReadModal";
import { pushApiError } from "../../store/notifications";
import { showToast } from "../ui/Toast";
import { cn } from "../ui/cn";
import { isSingleLineDescription } from "../../lib/description";

interface ItemDescriptionProps {
  namespace: string;
  path: string;
  description?: string;
  canEdit: boolean;
}

export function ItemDescription({
  namespace,
  path,
  description,
  canEdit,
}: ItemDescriptionProps) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [readOpen, setReadOpen] = useState(false);
  const [needsCollapse, setNeedsCollapse] = useState<boolean | null>(null);
  const [text, setText] = useState(description ?? "");
  const contentRef = useRef<HTMLDivElement>(null);

  const mut = useMutation({
    mutationFn: () => treeApi.describe(namespace, path, { description: text }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["item", namespace, path] });
      showToast("Description saved");
      setEditing(false);
    },
    onError: (e: Error) => pushApiError("Failed to save description", e),
  });

  const hasDescription = Boolean(description?.trim());
  const singleLine = isSingleLineDescription(description ?? "");
  const multiLine = hasDescription && !singleLine;
  const collapsible = multiLine && needsCollapse === true;
  const isCollapsedView =
    multiLine &&
    (needsCollapse === null || (needsCollapse === true && !expanded));
  const isExpanded = singleLine || !isCollapsedView;

  useLayoutEffect(() => {
    setExpanded(false);
    setNeedsCollapse(null);
  }, [description]);

  useLayoutEffect(() => {
    if (!multiLine) {
      setNeedsCollapse(false);
      return;
    }

    const el = contentRef.current;
    if (!el) return;

    const measureNeedsCollapse = () => {
      const previousMaxHeight = el.style.maxHeight;
      const previousOverflow = el.style.overflow;
      el.style.maxHeight = "calc(2 * 0.75rem * 1.625)";
      el.style.overflow = "hidden";
      const overflows = el.scrollHeight > el.clientHeight + 1;
      el.style.maxHeight = previousMaxHeight;
      el.style.overflow = previousOverflow;
      setNeedsCollapse(overflows);
    };

    measureNeedsCollapse();

    if (typeof ResizeObserver === "undefined") return;

    const observer = new ResizeObserver(measureNeedsCollapse);
    observer.observe(el);
    return () => observer.disconnect();
  }, [description, multiLine]);

  if (!description && !canEdit) return null;

  const handleCollapsedClick = () => {
    if (!collapsible || isExpanded) return;
    const selection = window.getSelection();
    if (selection && selection.toString().length > 0) return;
    setExpanded(true);
  };

  return (
    <div className="border-b px-6 py-2 dark:border-gray-700">
      <DescriptionReadModal
        open={readOpen}
        onClose={() => setReadOpen(false)}
        description={description ?? ""}
      />
      {editing ? (
        <div className="space-y-2">
          <MarkdownEditor
            value={text}
            onChange={setText}
            rows={5}
            textareaClassName="text-xs"
          />
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              loading={mut.isPending}
              onClick={() => mut.mutate()}
            >
              <Save className="h-3.5 w-3.5" />
              Save
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setEditing(false);
                setText(description ?? "");
              }}
            >
              <X className="h-3.5 w-3.5" />
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="group flex items-start gap-2">
          <div className="min-w-0 flex-1">
            {hasDescription ? (
              <div
                role={collapsible && !isExpanded ? "button" : undefined}
                tabIndex={collapsible && !isExpanded ? 0 : undefined}
                onClick={handleCollapsedClick}
                onKeyDown={(e) => {
                  if (
                    (e.key === "Enter" || e.key === " ") &&
                    collapsible &&
                    !isExpanded
                  ) {
                    e.preventDefault();
                    setExpanded(true);
                  }
                }}
                className={cn(
                  collapsible && !isExpanded && "cursor-pointer",
                  collapsible && !isExpanded && "group/desc",
                )}
              >
                <div
                  className={cn(
                    "relative",
                    collapsible &&
                      !isExpanded && [
                        "after:pointer-events-none after:absolute after:inset-x-0 after:bottom-0 after:z-10 after:h-7 after:content-['']",
                        "after:bg-gradient-to-t after:from-slate-900/[0.05] after:to-transparent",
                        "dark:after:from-black/25 dark:after:to-transparent",
                      ],
                  )}
                >
                  <div
                    ref={contentRef}
                    className={cn(
                      isCollapsedView && "item-markdown-collapsed",
                      collapsible && expanded && "item-markdown-panel",
                    )}
                  >
                    <DescriptionMarkdown className="select-text">
                      {description!}
                    </DescriptionMarkdown>
                  </div>
                  {collapsible && !isExpanded && (
                    <div
                      aria-hidden
                      className={cn(
                        "pointer-events-none absolute inset-x-0 bottom-0 z-20 flex justify-center pb-0.5",
                        "opacity-0 transition-opacity duration-150",
                        "group-hover/desc:opacity-100 group-focus-within/desc:opacity-100",
                      )}
                    >
                      <span className="flex items-center justify-center rounded-full bg-surface-elevated/95 px-1.5 py-0.5 text-gray-500 shadow-sm ring-1 ring-slate-300/50 dark:bg-gray-900/95 dark:text-gray-400 dark:ring-gray-600">
                        <ChevronDown className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs leading-[1.5rem] text-gray-400/80 dark:text-gray-500/80">
                No description
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-0.5 pt-0.5">
            {collapsible && expanded && (
              <>
                <button
                  type="button"
                  onClick={() => setReadOpen(true)}
                  className="rounded p-1 text-gray-400 opacity-0 transition-opacity hover:bg-slate-200 hover:text-gray-600 group-hover:opacity-100 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                  title="View full description"
                >
                  <Maximize2 className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setExpanded(false)}
                  className="rounded p-1 text-gray-400 opacity-0 transition-opacity hover:bg-slate-200 hover:text-gray-600 group-hover:opacity-100 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                  title="Collapse description"
                >
                  <ChevronUp className="h-3.5 w-3.5" />
                </button>
              </>
            )}
            {canEdit && (isExpanded || !hasDescription) && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className={cn(
                  "rounded p-1 text-gray-400 hover:bg-slate-200 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-200",
                  hasDescription &&
                    "opacity-0 transition-opacity group-hover:opacity-100",
                )}
                title="Edit description"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
