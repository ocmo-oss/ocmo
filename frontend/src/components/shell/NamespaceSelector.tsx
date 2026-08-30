import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, House, LayoutGrid, Search } from "lucide-react";
import { namespacesApi } from "../../api/namespaces";
import { useDefaultNamespace } from "../../store/defaultNamespace";
import { cn } from "../ui/cn";

export function NamespaceSelector() {
  const { namespace } = useParams<{ namespace: string }>();
  const navigate = useNavigate();
  const { namespace: defaultNamespace } = useDefaultNamespace();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["namespaces", query],
    queryFn: ({ signal }) =>
      namespacesApi.list(
        { name_filter: query || undefined, limit: 50 },
        signal,
      ),
    enabled: open,
    staleTime: 30_000,
  });

  const namespaces = useMemo(() => data?.items ?? [], [data]);

  useEffect(() => {
    if (open) {
      const t = setTimeout(() => inputRef.current?.focus(), 0);
      return () => clearTimeout(t);
    }
    setQuery("");
  }, [open]);

  if (!namespace) return null;

  const selectNamespace = (name: string) => {
    navigate(`/ns/${name}/configs`);
    setOpen(false);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-gray-700 hover:bg-slate-200 dark:text-gray-200 dark:hover:bg-gray-800"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className="font-mono text-xs bg-slate-200 dark:bg-gray-800 px-1.5 py-0.5 rounded text-brand-700 dark:text-brand-300">
          {namespace}
        </span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 text-gray-400 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full z-40 mt-1 w-72 rounded-lg border bg-surface-elevated shadow-lg dark:border-gray-700 dark:bg-gray-900">
            <div className="border-b p-2 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
                <input
                  ref={inputRef}
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search namespaces…"
                  className="w-full rounded-md border border-slate-300 bg-surface-elevated py-1.5 pl-8 pr-2 text-sm text-gray-800 placeholder-gray-400 focus:border-brand-400 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                />
              </div>
            </div>
            <ul className="max-h-64 overflow-y-auto py-1" role="listbox">
              {isLoading && (
                <li className="px-3 py-2 text-xs text-gray-400">Loading…</li>
              )}
              {!isLoading && namespaces.length === 0 && (
                <li className="px-3 py-2 text-xs text-gray-400">
                  No namespaces found
                </li>
              )}
              {namespaces.map((ns) => (
                <li key={ns.name}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={ns.name === namespace}
                    onClick={() => selectNamespace(ns.name)}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-gray-800",
                      ns.name === namespace
                        ? "font-medium text-brand-700 dark:text-brand-300"
                        : "text-gray-700 dark:text-gray-200",
                    )}
                  >
                    <span className="flex h-3.5 w-3.5 shrink-0 items-center justify-center">
                      {defaultNamespace === ns.name && (
                        <House
                          className="h-3.5 w-3.5 fill-current text-brand-600 dark:text-brand-400"
                          aria-label="Default namespace"
                        />
                      )}
                    </span>
                    <span className="font-mono text-xs">{ns.name}</span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="border-t p-1 dark:border-gray-700">
              <Link
                to="/namespaces"
                onClick={() => setOpen(false)}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-xs text-gray-600 hover:bg-slate-100 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                All namespaces
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
