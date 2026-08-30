import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Search } from "lucide-react";
import { resolveApi } from "../../api/resolve";
import { cn } from "../ui/cn";

interface CastFormatSelectorProps {
  value: string;
  onChange: (format: string) => void;
}

export function CastFormatSelector({
  value,
  onChange,
}: CastFormatSelectorProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["cast-formats"],
    queryFn: ({ signal }) => resolveApi.castFormats(signal),
    staleTime: 60_000,
  });

  const formats = data?.formats ?? [];
  const normalizedQuery = query.trim().toLowerCase();

  const filtered = useMemo(() => {
    if (!normalizedQuery) return formats;
    return formats.filter((f) =>
      f.format.toLowerCase().includes(normalizedQuery),
    );
  }, [formats, normalizedQuery]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setHighlighted(0);
    }
  }, [open]);

  useEffect(() => {
    setHighlighted(0);
  }, [query, filtered.length]);

  const select = (format: string) => {
    onChange(format);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filtered[highlighted]) {
      e.preventDefault();
      select(filtered[highlighted]!.format);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const label = value || "default (yaml)";

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center justify-between gap-1 rounded-md border px-2 py-1.5 text-left text-xs font-mono",
          "border-slate-300 bg-surface-elevated text-gray-700 hover:border-brand-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200",
        )}
      >
        <span className="truncate">{label}</span>
        <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute left-0 right-0 top-full z-40 mt-1 rounded-lg border bg-surface-elevated shadow-lg dark:border-gray-700 dark:bg-gray-900">
            <div className="border-b p-2 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-3 w-3 -translate-y-1/2 text-gray-400" />
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={onKeyDown}
                  placeholder="Search formats…"
                  className="w-full rounded-md border border-slate-300 bg-surface-elevated py-1 pl-7 pr-2 text-xs text-gray-800 placeholder-gray-400 focus:border-brand-400 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                  autoFocus
                />
              </div>
            </div>
            <div ref={listRef} className="max-h-48 overflow-y-auto">
              <button
                type="button"
                onMouseEnter={() => setHighlighted(0)}
                onClick={() => select("")}
                className={cn(
                  "flex w-full px-3 py-2 text-left text-xs hover:bg-slate-100 dark:hover:bg-gray-800",
                  !value && "bg-brand-50 dark:bg-brand-900/20",
                  highlighted === 0 && "bg-surface dark:bg-gray-800",
                )}
              >
                default (yaml)
              </button>
              {isLoading && (
                <p className="px-3 py-2 text-xs text-gray-400">Loading…</p>
              )}
              {filtered.map((item, index) => {
                const idx = index + 1;
                return (
                  <button
                    key={item.format}
                    type="button"
                    onMouseEnter={() => setHighlighted(idx)}
                    onClick={() => select(item.format)}
                    className={cn(
                      "flex w-full px-3 py-2 text-left font-mono text-xs hover:bg-slate-100 dark:hover:bg-gray-800",
                      value === item.format &&
                        "bg-brand-50 dark:bg-brand-900/20",
                      highlighted === idx && "bg-surface dark:bg-gray-800",
                    )}
                  >
                    {item.format}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
