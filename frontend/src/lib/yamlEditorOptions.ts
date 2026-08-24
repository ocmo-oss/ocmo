import type { editor } from 'monaco-editor'

/** Shared Monaco options for YAML config/resolver editors with schema completion. */
export function yamlEditorOptions(readOnly = false): editor.IStandaloneEditorConstructionOptions {
  return {
    minimap: { enabled: false },
    fontSize: 13,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    readOnly,
    accessibilitySupport: 'on',
    fixedOverflowWidgets: true,
    quickSuggestions: {
      other: true,
      comments: false,
      strings: true,
    },
    suggestOnTriggerCharacters: true,
    suggest: {
      preview: true,
      showIcons: true,
      showStatusBar: true,
      previewMode: 'subwordSmart',
      showWords: false,
    },
    wordBasedSuggestions: 'off',
  }
}
