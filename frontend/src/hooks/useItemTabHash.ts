import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const TAB_TO_HASH: Record<string, string> = {
  change_requests: "change-requests",
};

const HASH_TO_TAB: Record<string, string> = {
  "change-requests": "change_requests",
};

/** URL hash fragment for an item tab (no hash when tab is the default). */
export function itemTabToHash(tab: string, defaultTab: string): string {
  if (tab === defaultTab) return "";
  const segment = TAB_TO_HASH[tab] ?? tab;
  return `#${segment}`;
}

/** Parse location hash into a tab id if it matches one of `validTabs`. */
export function parseItemTabHash<T extends string>(
  hash: string,
  validTabs: readonly T[],
): T | null {
  const segment = decodeURIComponent(
    hash.replace(/^#/, "").trim(),
  ).toLowerCase();
  if (!segment) return null;
  const tab = (HASH_TO_TAB[segment] ?? segment) as T;
  return validTabs.includes(tab) ? tab : null;
}

type UseItemTabHashOptions<T extends string> = {
  /** Used when the URL has no hash (or an unknown hash). */
  initialWhenNoHash?: T;
};

export function useItemTabHash<T extends string>(
  validTabs: readonly T[],
  defaultTab: T,
  options?: UseItemTabHashOptions<T>,
): [T, (tab: T) => void] {
  const location = useLocation();
  const navigate = useNavigate();
  const validKey = useMemo(() => validTabs.join("\0"), [validTabs]);
  const fallbackNoHash = options?.initialWhenNoHash ?? defaultTab;

  const resolveTab = useCallback((): T => {
    const fromHash = parseItemTabHash(location.hash, validTabs);
    if (fromHash) return fromHash;
    return fallbackNoHash;
  }, [location.hash, validKey, validTabs, fallbackNoHash]);

  const [activeTab, setActiveTabState] = useState<T>(resolveTab);

  useEffect(() => {
    setActiveTabState(resolveTab());
  }, [location.pathname, location.hash, resolveTab]);

  useEffect(() => {
    if (!validTabs.includes(activeTab)) {
      setActiveTabState(defaultTab);
      const hash = itemTabToHash(defaultTab, defaultTab);
      navigate(
        { pathname: location.pathname, search: location.search, hash },
        { replace: true },
      );
    }
  }, [
    activeTab,
    defaultTab,
    location.pathname,
    location.search,
    navigate,
    validKey,
    validTabs,
  ]);

  const setActiveTab = useCallback(
    (tab: T) => {
      setActiveTabState(tab);
      const hash = itemTabToHash(tab, defaultTab);
      navigate(
        { pathname: location.pathname, search: location.search, hash },
        { replace: true },
      );
    },
    [defaultTab, location.pathname, location.search, navigate],
  );

  return [activeTab, setActiveTab];
}
