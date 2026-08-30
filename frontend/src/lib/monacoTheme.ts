import type * as Monaco from "monaco-editor";
import type { Theme } from "../store/theme";

const OCMO_LIGHT = "ocmo-light";
const OCMO_DARK = "ocmo-dark";

let themesRegistered = false;

/** Register OCMO editor themes once Monaco is loaded. */
export function defineMonacoThemes(monaco: typeof Monaco): void {
  if (themesRegistered) return;
  themesRegistered = true;

  monaco.editor.defineTheme(OCMO_LIGHT, {
    base: "vs",
    inherit: true,
    rules: [],
    colors: {
      "editor.background": "#e9eef4",
      "editor.foreground": "#334155",
      "editorLineNumber.foreground": "#94a3b8",
      "editorLineNumber.activeForeground": "#64748b",
      "editor.lineHighlightBackground": "#dfe6ee",
      "editor.selectionBackground": "#b6ccf680",
      "editor.inactiveSelectionBackground": "#d5dde8",
      "editor.selectionHighlightBackground": "#c8d5e699",
      "editorCursor.foreground": "#2563eb",
      "editorWhitespace.foreground": "#cbd5e180",
      "editorIndentGuide.background": "#c5d0dc",
      "editorIndentGuide.activeBackground": "#a8b8c8",
      "editorWidget.background": "#f5f8fb",
      "editorWidget.border": "#c5d0dc",
      "editorSuggestWidget.background": "#f5f8fb",
      "editorSuggestWidget.border": "#c5d0dc",
      "editorHoverWidget.background": "#f5f8fb",
      "editorHoverWidget.border": "#c5d0dc",
      "scrollbarSlider.background": "#a8b8c866",
      "scrollbarSlider.hoverBackground": "#94a3b899",
      "scrollbarSlider.activeBackground": "#7f8fa3b3",
      "minimap.background": "#e9eef4",
    },
  });

  monaco.editor.defineTheme(OCMO_DARK, {
    base: "vs-dark",
    inherit: true,
    rules: [],
    colors: {
      "editor.background": "#0c0f14",
      "editor.lineHighlightBackground": "#151a22",
      "editorWidget.background": "#11151c",
      "editorSuggestWidget.background": "#11151c",
      "editorHoverWidget.background": "#11151c",
      "minimap.background": "#0c0f14",
    },
  });
}

export function monacoEditorTheme(appTheme: Theme): string {
  return appTheme === "dark" ? OCMO_DARK : OCMO_LIGHT;
}
