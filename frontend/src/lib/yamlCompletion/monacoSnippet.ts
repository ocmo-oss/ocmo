/**
 * Escape literal `$` in Monaco snippet insert text.
 * Without this, keys like `$schema` are parsed as snippet tab stops.
 */
export function escapeMonacoSnippetDollars(text: string): string {
  return text.replace(/\$(?=[_a-zA-Z])/g, "\\$");
}
