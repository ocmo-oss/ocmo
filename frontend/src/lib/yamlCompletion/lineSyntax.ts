/** Pure line-level syntax helpers — no imports, no Monaco, no schema logic. */

export function lineKey(line: string): string | null {
  const trimmed = line.trim();
  const quoted = trimmed.match(/^["']([^"']+)["']\s*:/);
  if (quoted) return quoted[1];
  const bare = trimmed.match(/^(\$?[\w][\w@./_-]*)\s*:/);
  return bare?.[1] ?? null;
}

export function lineArrayItemKey(line: string): string | null {
  const trimmed = line.trim();
  const quoted = trimmed.match(/^-\s*["']([^"']+)["']\s*:/);
  if (quoted) return quoted[1];
  const bare = trimmed.match(/^-\s*(\$?[\w][\w@./_-]*)\s*:/);
  return bare?.[1] ?? null;
}

/** Returns true when the line starts an array item (dash alone or dash + space). */
export function isArrayItemLine(line: string): boolean {
  return /^\s*-(\s|$)/.test(line);
}

export function isEmptyScalarArrayItemLine(line: string): boolean {
  return /^\s*-\s*$/.test(line);
}

export function arrayItemLinePrefix(
  line: string,
): { dashEndColumn: number; hasDash: boolean } | null {
  const match = line.match(/^(\s*-\s*)/);
  if (!match || match.index === undefined) return null;
  return {
    hasDash: true,
    dashEndColumn: match.index + match[0].length + 1,
  };
}

export function isScalarArrayItemLine(line: string): boolean {
  if (!/^\s*-\s*\S/.test(line)) return false;
  return !/^[\w@./_-]+\s*:/.test(line.trimStart().replace(/^-\s*/, ""));
}

/** 1-indexed column of the first item character after "- " in an array item line. */
export function arrayItemValueStartColumn(line: string): number | null {
  const dashMatch = line.match(/^(\s*-\s*)/);
  if (!dashMatch || dashMatch.index === undefined) return null;
  return dashMatch.index + dashMatch[0].length + 1;
}

export function stripYamlScalarQuotes(value: string): string {
  const trimmed = value.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

export function needsLeadingSpaceAfterArrayDash(line: string): boolean {
  const match = line.match(/^(\s*-\s*)(.*)$/);
  if (!match) return false;
  return !match[1].endsWith(" ");
}

export function formatScalarArrayItemInsertText(
  line: string,
  insertText: string,
): string {
  if (!needsLeadingSpaceAfterArrayDash(line)) return insertText;
  return insertText.startsWith(" ") ? insertText : ` ${insertText}`;
}

export function arrayItemCount(schema: Record<string, unknown>): number {
  if (typeof schema.minItems === "number" && schema.minItems > 0) {
    return schema.minItems;
  }
  return 1;
}

export function bodyLineLeadingSpaces(line: string): number {
  return line.match(/^(\s*)/)?.[1].length ?? 0;
}
