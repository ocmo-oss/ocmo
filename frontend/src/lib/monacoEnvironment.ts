/**
 * Monaco web worker wiring for Vite.
 *
 * Must load before monaco-editor is initialized (import from main.tsx first).
 * Use package export paths (monaco-editor/editor/...), not esm/vs/... — the
 * latter is not exposed by monaco-editor's package.json exports map.
 *
 * `getWorkerUrl` + `?url` is inlined as data: URLs in production builds, which
 * strict `script-src 'self'` CSP rejects. Instantiate via Vite's `?worker`.
 */
import EditorWorker from "monaco-editor/editor/common/services/editorWebWorkerMain.js?worker";

globalThis.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    return new EditorWorker({ name: label });
  },
};
