/** Compress consecutive empty-folder segments in a path label. */
export function compressPath(
  segments: Array<{ name: string; hasContent: boolean }>,
): string {
  const parts: string[] = [];
  let buffer: string[] = [];

  for (const seg of segments) {
    if (!seg.hasContent) {
      buffer.push(seg.name);
    } else {
      if (buffer.length > 0) {
        parts.push(buffer.join(" / "));
        buffer = [];
      }
      parts.push(seg.name);
    }
  }
  if (buffer.length > 0) parts.push(buffer.join(" / "));
  return parts.join(" / ");
}

export function pathSegments(path: string): string[] {
  return path.split("/").filter(Boolean);
}

export function pathParent(path: string): string {
  const parts = path.split("/");
  parts.pop();
  return parts.join("/");
}

export function pathJoin(...parts: string[]): string {
  return parts.filter(Boolean).join("/").replace(/\/+/g, "/");
}
