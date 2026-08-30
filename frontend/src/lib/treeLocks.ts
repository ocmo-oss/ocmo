import type { Lock } from "../api/types";
import { normalizeTreePath } from "./builtinPaths";

export interface TreeLockInfo {
  lock: Lock;
  isDirect: boolean;
}

export function getLockForPath(
  path: string,
  locks: Lock[],
): TreeLockInfo | null {
  const normalized = normalizeTreePath(path);
  let inherited: TreeLockInfo | null = null;

  for (const lock of locks) {
    const lockPath = normalizeTreePath(lock.path);
    if (normalized === lockPath) {
      return { lock, isDirect: true };
    }
    if (normalized.startsWith(`${lockPath}/`)) {
      if (
        !inherited ||
        lockPath.length > normalizeTreePath(inherited.lock.path).length
      ) {
        inherited = { lock, isDirect: false };
      }
    }
  }

  return inherited;
}
