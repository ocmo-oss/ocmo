export function isTreeNodeVisible(
  path: string,
  matchingPaths: Set<string>,
  searchActive = false,
): boolean {
  if (searchActive && matchingPaths.size === 0) return false
  if (matchingPaths.size === 0) return true
  for (const match of matchingPaths) {
    if (match === path) return true
    if (match.startsWith(`${path}/`)) return true
    if (path.startsWith(`${match}/`)) return true
  }
  return false
}

export function isTreeFolderAutoExpanded(folderPath: string, matchingPaths: Set<string>): boolean {
  if (matchingPaths.size === 0) return false
  for (const match of matchingPaths) {
    if (match.startsWith(`${folderPath}/`)) return true
  }
  return false
}
