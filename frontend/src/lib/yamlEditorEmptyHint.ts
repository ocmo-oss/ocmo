import type { editor } from "monaco-editor";
import type * as Monaco from "monaco-editor";
import { installEditorEmptyHint } from "./editorEmptyHint";

const HINT_TEXT = "Press Ctrl+Space to show input suggestions";

export interface YamlEditorEmptyHintOptions {
  /** When false the hint is never shown (e.g. schema not loaded yet). */
  hasSuggestions?: () => boolean;
}

export function installYamlEditorEmptyHint(
  editorInstance: editor.IStandaloneCodeEditor,
  monaco: typeof Monaco,
  options: YamlEditorEmptyHintOptions = {},
): Monaco.IDisposable & { refresh: () => void } {
  return installEditorEmptyHint(editorInstance, monaco, {
    text: HINT_TEXT,
    enabled: () => options.hasSuggestions?.() ?? true,
  });
}
