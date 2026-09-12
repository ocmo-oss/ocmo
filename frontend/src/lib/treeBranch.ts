/** True when `itemPath` is the folder itself or a descendant of `folderPath`. */
export function isPathUnderFolder(
  folderPath: string,
  itemPath: string,
): boolean {
  return itemPath === folderPath || itemPath.startsWith(`${folderPath}/`);
}
