/** URL for opening a tree item from the sidebar (non-folder items default to latest tag). */
export function treeItemHref(
  namespace: string,
  path: string,
  isFolder = false,
): string {
  const base = `/ns/${namespace}/configs/${path}`;
  return isFolder ? base : `${base}?tag=latest`;
}
