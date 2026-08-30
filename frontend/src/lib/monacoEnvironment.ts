/**
 * Monaco web worker wiring for Vite.
 *
 * Must load before monaco-editor is initialized (import from main.tsx first).
 * Use package export paths (monaco-editor/editor/...), not esm/vs/... — the
 * latter is not exposed by monaco-editor's package.json exports map.
 */
import editorWorkerUrl from "monaco-editor/editor/common/services/editorWebWorkerMain.js?url";

globalThis.MonacoEnvironment = {
  getWorkerUrl(_workerId: string, _label: string) {
    return editorWorkerUrl;
  },
};
