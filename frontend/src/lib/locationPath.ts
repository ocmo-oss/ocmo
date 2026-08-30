import { normalizeTreePath } from "./builtinPaths";
import { pathJoin } from "./paths";

const TREE_PATH_SEGMENT_RE = /^[a-zA-Z0-9_.-]+$/;
const TREE_PATH_ALLOWED_CHAR_RE = /[a-zA-Z0-9_.\-/]/;

function isCommittablePathSegment(segment: string): boolean {
  return Boolean(segment) && segment !== "." && segment !== "..";
}

/** Keep only characters allowed in tree paths while the user types. */
export function filterTreePathInput(raw: string): string {
  const filtered = [...raw]
    .filter((char) => TREE_PATH_ALLOWED_CHAR_RE.test(char))
    .join("")
    .replace(/^\/+/, "")
    .replace(/\/+/g, "/");
  return filtered;
}

/** Split sanitized suffix input into committed prefix segments and the active tail. */
export function splitTreePathSuffixInput(nextInput: string): {
  completedSegments: string[];
  currentInput: string;
} {
  const sanitized = filterTreePathInput(nextInput);
  if (!sanitized.includes("/")) {
    return { completedSegments: [], currentInput: sanitized };
  }

  const parts = sanitized.split("/");
  const completedSegments = parts.slice(0, -1).filter(isCommittablePathSegment);
  const currentInput = parts[parts.length - 1] ?? "";

  return { completedSegments, currentInput };
}

export function validateTreePathCharacters(path: string): string | undefined {
  const normalized = normalizeTreePath(path);
  if (!normalized) {
    return undefined;
  }

  const segments = normalized.split("/");
  if (segments.some((segment) => segment === "." || segment === "..")) {
    return "Path segments '.' and '..' are not allowed";
  }

  if (!segments.every((segment) => TREE_PATH_SEGMENT_RE.test(segment))) {
    return "Path may only contain letters, numbers, underscores, hyphens, and dots, separated by slashes";
  }

  return undefined;
}

/** Build a relocation destination path from a selected parent folder and item name. */
export function buildDestinationPathFromFolder(
  folderPath: string,
  itemName: string,
): string {
  const parent = normalizeTreePath(folderPath);
  const name = normalizeTreePath(itemName);
  if (!name) {
    return filterTreePathInput(parent);
  }
  if (!parent) {
    return filterTreePathInput(name);
  }
  return filterTreePathInput(pathJoin(parent, name));
}

export function isPathUnderPrefix(
  itemPath: string,
  prefixPath: string,
): boolean {
  if (!prefixPath) return itemPath.includes("/");
  return itemPath === prefixPath || itemPath.startsWith(`${prefixPath}/`);
}

export function validateRelocationTargetPath(
  source: string,
  target: string,
  mode: "move" | "copy",
): string | undefined {
  const normalizedSource = normalizeTreePath(source);
  const normalizedTarget = normalizeTreePath(target);

  const characterError = validateTreePathCharacters(target);
  if (characterError) {
    return characterError;
  }

  if (!normalizedTarget) return "Destination path is required";
  if (normalizedTarget === normalizedSource) {
    return "Destination must differ from the source path";
  }
  if (
    mode === "move" &&
    isPathUnderPrefix(normalizedTarget, normalizedSource)
  ) {
    return "Destination cannot be under the source path";
  }
  return undefined;
}
