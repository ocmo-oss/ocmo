import { pathSegments } from "./paths";

/** Parent folder of a config/template path (OCMO relative-path base). */
export function configParentFolder(itemPath: string): string {
  const parts = pathSegments(itemPath);
  if (parts.length <= 1) return "";
  return parts.slice(0, -1).join("/");
}

/** Split ``path[@version]`` — mirrors API ``parse_ref``. */
export function splitOcmoReference(ref: string): {
  pathPart: string;
  suffix: string;
} {
  const at = ref.lastIndexOf("@");
  if (at < 0) {
    return { pathPart: ref, suffix: "" };
  }
  return {
    pathPart: ref.slice(0, at),
    suffix: ref.slice(at),
  };
}

/** Resolve ``./`` / ``../`` against the config's parent folder — mirrors API ``resolve_relative_path``. */
export function resolveRelativeOcmoPath(
  baseConfigPath: string,
  refPath: string,
): string {
  const isRelative =
    refPath === "." ||
    refPath === ".." ||
    refPath.startsWith("./") ||
    refPath.startsWith("../");
  if (isRelative) {
    const baseFolder = configParentFolder(baseConfigPath);
    const baseSegments = pathSegments(baseFolder);
    for (const seg of refPath.split("/")) {
      if (seg === "..") {
        if (baseSegments.length > 0) baseSegments.pop();
      } else if (seg === "" || seg === ".") {
        continue;
      } else {
        baseSegments.push(seg);
      }
    }
    return baseSegments.join("/");
  }
  return refPath.replace(/^\/+/, "").replace(/\/+$/, "");
}

export function isRelativePath(refPath: string): boolean {
  return (
    refPath === "." ||
    refPath === ".." ||
    refPath.startsWith("./") ||
    refPath.startsWith("../")
  );
}

export type OcmoReferenceStyle = "absolute" | "relative";

export function referenceStyle(pathPart: string): OcmoReferenceStyle {
  return isRelativePath(pathPart) ? "relative" : "absolute";
}

/**
 * User finished typing relative directory navigation only (e.g. ``../``, ``../../``)
 * and wants siblings in the resolved folder — not a partial filename yet.
 */
export function isRelativeDirectoryBrowse(typedPathPart: string): boolean {
  if (!isRelativePath(typedPathPart)) return false;
  if (typedPathPart.endsWith("/")) return true;
  const rest = typedPathPart.replace(/^(?:\.\.\/|\.\/)+/, "");
  return rest === "" || rest === "." || rest === "..";
}

/** Browse mode: list direct children of a resolved folder prefix. */
export function isDirectoryBrowsePrefix(
  typedPathPart: string,
  resolvedPrefix: string,
): boolean {
  if (!resolvedPrefix) return false;
  return (
    isRelativeDirectoryBrowse(typedPathPart) || typedPathPart.endsWith("/")
  );
}

export function isDirectChildOf(itemPath: string, folderPath: string): boolean {
  return configParentFolder(itemPath) === folderPath;
}

/** True when an item path is the folder itself or any descendant under it. */
export function isUnderFolderPrefix(
  itemPath: string,
  folderPath: string,
): boolean {
  if (!folderPath) return !itemPath.includes("/");
  return itemPath === folderPath || itemPath.startsWith(`${folderPath}/`);
}

/** Convert an absolute tree path to a relative reference from the config's folder. */
export function toRelativeOcmoPath(
  baseConfigPath: string,
  absolutePath: string,
): string {
  const baseDir = configParentFolder(baseConfigPath);
  const baseParts = pathSegments(baseDir);
  const absParts = pathSegments(absolutePath);

  let common = 0;
  while (
    common < baseParts.length &&
    common < absParts.length &&
    baseParts[common] === absParts[common]
  ) {
    common += 1;
  }

  const ups = baseParts.length - common;
  const tail = absParts.slice(common);
  if (ups === 0) {
    return tail.length === 0 ? "." : `./${tail.join("/")}`;
  }
  const rel = [...Array(ups).fill(".."), ...tail];
  return rel.join("/");
}

/** Format a picked absolute path for insertion, preserving relative style when the user started one. */
export function formatOcmoReferenceInsert(
  baseConfigPath: string,
  absolutePath: string,
  typedPathPart: string,
  suffix: string,
): string {
  const path =
    referenceStyle(typedPathPart) === "relative"
      ? toRelativeOcmoPath(baseConfigPath, absolutePath)
      : absolutePath;
  return `${path}${suffix}`;
}

/** Minimum characters in the typed path before searching. */
export const MIN_URI_REFERENCE_SEARCH_LEN = 2;

/** Last path segment used as the API search query token. */
export function searchQueryToken(resolvedPrefix: string): string | null {
  const segments = pathSegments(resolvedPrefix.replace(/\/+$/, ""));
  if (segments.length === 0) return null;
  return segments[segments.length - 1] ?? null;
}

/** True when enough of the path has been typed to query the tree search API. */
export function isUriReferenceSearchReady(resolvedPrefix: string): boolean {
  const normalized = resolvedPrefix.trim();
  if (normalized.length < MIN_URI_REFERENCE_SEARCH_LEN) return false;

  const segments = pathSegments(normalized.replace(/\/+$/, ""));
  const last = segments[segments.length - 1] ?? "";
  if (last.length >= MIN_URI_REFERENCE_SEARCH_LEN) return true;

  // Multi-segment paths like `test/e` — parent segments give enough context.
  return (
    segments.length > 1 &&
    normalized.replace(/\//g, "").length >= MIN_URI_REFERENCE_SEARCH_LEN
  );
}

/**
 * Match item paths against a typed prefix.
 * Supports partial final segments (`te` → `test/...`) and full path prefixes (`test/emp` → `test/empty/...`).
 */
export function pathMatchesTypedPrefix(
  itemPath: string,
  resolvedPrefix: string,
): boolean {
  const normalizedPrefix = resolvedPrefix.replace(/\/+$/, "");
  if (!normalizedPrefix) return true;

  if (
    itemPath === normalizedPrefix ||
    itemPath.startsWith(`${normalizedPrefix}/`)
  ) {
    return true;
  }

  const prefixParts = pathSegments(normalizedPrefix);
  const pathParts = pathSegments(itemPath);
  if (prefixParts.length === 0) return true;

  for (let i = 0; i < prefixParts.length - 1; i++) {
    if (pathParts[i] !== prefixParts[i]) return false;
  }

  const partial = prefixParts[prefixParts.length - 1]!;
  const pathSegment = pathParts[prefixParts.length - 1];
  if (!pathSegment) return false;

  return pathSegment.startsWith(partial);
}

/** @deprecated Use pathMatchesTypedPrefix */
export function pathMatchesPrefix(
  itemPath: string,
  resolvedPrefix: string,
): boolean {
  return pathMatchesTypedPrefix(itemPath, resolvedPrefix);
}
