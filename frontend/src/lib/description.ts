export function isSingleLineDescription(description: string): boolean {
  const trimmed = description.trim();
  return trimmed.length > 0 && !/[\r\n]/.test(trimmed);
}
