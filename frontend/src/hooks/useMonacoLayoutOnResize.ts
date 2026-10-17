import { useEffect, type RefObject } from "react";
import type { editor } from "monaco-editor";

/** Calls Monaco `layout()` when the container size changes (e.g. focus mode transitions). */
export function useMonacoLayoutOnResize(
  containerRef: RefObject<HTMLElement | null>,
  editorRef: RefObject<editor.IStandaloneCodeEditor | null>,
) {
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const ro = new ResizeObserver(() => {
      editorRef.current?.layout();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [containerRef, editorRef]);
}
