import { useEffect } from "react";
import { Search, X } from "lucide-react";
import { useTreeSearchStore } from "../../store/treeSearch";

export function TreeSearch() {
  const { query, setQuery, setDebouncedQuery, clear } = useTreeSearchStore();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query, setDebouncedQuery]);

  return (
    <div className="relative">
      <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search"
        className="w-full rounded-md border border-slate-300 bg-surface-elevated py-1.5 pl-8 pr-8 text-sm text-gray-800 placeholder-gray-400 focus:border-brand-400 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
      />
      {query && (
        <button
          onClick={clear}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
