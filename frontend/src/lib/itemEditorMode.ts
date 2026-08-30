export type ItemEditorMode = "create" | "edit";

export function isCreateMode(mode: ItemEditorMode): boolean {
  return mode === "create";
}

export function hasEditorContent(content: string): boolean {
  return content.trim().length > 0;
}
