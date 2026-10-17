import { useEffect, useRef, type ReactNode, type RefObject } from "react";
import type { editor } from "monaco-editor";
import { isModalOpen } from "../../../store/modalStack";
import { useMonacoLayoutOnResize } from "../../../hooks/useMonacoLayoutOnResize";
import { useEditorFocusGeometry } from "../../../hooks/useEditorFocusGeometry";
import { EditorFocusBackdrop } from "./EditorFocusBackdrop";
import { EditorFocusToolbar } from "./EditorFocusToolbar";
import { cn } from "../../ui/cn";

export function EditorFocusSurface({
  focusOpen,
  onCloseFocus,
  resolveSplitOpen = false,
  anchorMinHeight,
  editorRef,
  toolbarSave,
  toolbarResolve,
  children,
  className,
}: {
  focusOpen: boolean;
  onCloseFocus: () => void;
  resolveSplitOpen?: boolean;
  anchorMinHeight?: number;
  editorRef?: RefObject<editor.IStandaloneCodeEditor | null>;
  toolbarSave?: ReactNode;
  toolbarResolve?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const anchorRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const { isFocusActive, backdropShow, backdropDimmed, panelStyle } =
    useEditorFocusGeometry({
      focusOpen,
      resolveSplitOpen,
      anchorRef,
    });

  useMonacoLayoutOnResize(contentRef, editorRef ?? { current: null });

  useEffect(() => {
    if (!focusOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented) return;
      if (isModalOpen()) return;
      onCloseFocus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusOpen, onCloseFocus]);

  const showToolbar = focusOpen;

  return (
    <div
      ref={anchorRef}
      className={cn("relative min-h-0 min-w-0 flex-1", className)}
      style={
        isFocusActive && anchorMinHeight
          ? { minHeight: anchorMinHeight }
          : undefined
      }
    >
      <div
        role={focusOpen ? "dialog" : undefined}
        aria-modal={focusOpen ? true : undefined}
        className={cn(
          "flex min-h-0 flex-col overflow-hidden",
          isFocusActive
            ? "bg-surface-elevated shadow-2xl dark:bg-gray-950"
            : "relative h-full w-full",
          isFocusActive && !resolveSplitOpen && "rounded-lg",
          isFocusActive && resolveSplitOpen && "rounded-none",
        )}
        style={isFocusActive ? panelStyle : undefined}
        onClick={(e) => e.stopPropagation()}
      >
        {showToolbar && (
          <EditorFocusToolbar
            onExit={onCloseFocus}
            saveButton={toolbarSave}
            resolveButton={toolbarResolve}
          />
        )}
        <div
          ref={contentRef}
          className="min-h-0 min-w-0 flex-1 overflow-hidden"
        >
          {children}
        </div>
      </div>
      <EditorFocusBackdrop
        show={backdropShow}
        dimmed={backdropDimmed}
        onClose={onCloseFocus}
      />
    </div>
  );
}
