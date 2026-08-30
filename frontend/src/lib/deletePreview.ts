import type { ItemType } from "../api/types";

export interface DeletePreviewEntry {
  type: ItemType;
  path: string;
}

const DELETE_PREVIEW_RE = /^[^:]+::\s*(\w+)::\s*(.+)$/;

const TYPE_BY_LABEL: Record<string, ItemType> = {
  folder: "folder",
  config: "config",
  template: "template",
  secret: "secret",
  resolver: "resolver",
};

/** Parse API delete-preview lines like `my-ns:: Config:: app/foo`. */
export function parseDeletePreviewLine(line: string): DeletePreviewEntry {
  const trimmed = line.trim();
  const match = trimmed.match(DELETE_PREVIEW_RE);
  if (!match) {
    return { type: "config", path: trimmed };
  }

  const type = TYPE_BY_LABEL[match[1].toLowerCase()];
  if (!type) {
    return { type: "config", path: match[2] };
  }

  return { type, path: match[2] };
}

export function parseDeletePreviewLines(lines: string[]): DeletePreviewEntry[] {
  return lines.map(parseDeletePreviewLine);
}
