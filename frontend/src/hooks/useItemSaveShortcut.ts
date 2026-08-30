import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import type { editor } from "monaco-editor";
import type * as Monaco from "monaco-editor";
import { installEditorSaveShortcut } from "../lib/editorSaveShortcut";

const ENTER_TO_SAVE_HINT = "Press Enter to save";

export function useItemSaveShortcut({
  canSave,
  onSave,
}: {
  canSave: boolean;
  onSave: () => void;
}) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [showEnterHint, setShowEnterHint] = useState(false);
  const canSaveRef = useRef(canSave);
  const onSaveRef = useRef(onSave);
  const editorInstanceRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const shortcutDisposableRef = useRef<Monaco.IDisposable | null>(null);
  canSaveRef.current = canSave;
  onSaveRef.current = onSave;

  const focusSaveButton = useCallback(() => {
    if (!canSaveRef.current) return;
    setShowEnterHint(true);
    buttonRef.current?.focus({ preventScroll: true });
  }, []);

  const focusSaveButtonRef = useRef(focusSaveButton);
  focusSaveButtonRef.current = focusSaveButton;

  const installShortcut = useCallback(() => {
    const editorInstance = editorInstanceRef.current;
    const monaco = monacoRef.current;
    if (!editorInstance || !monaco) return;
    shortcutDisposableRef.current?.dispose();
    shortcutDisposableRef.current = installEditorSaveShortcut(
      editorInstance,
      monaco,
      () => focusSaveButtonRef.current,
    );
  }, []);

  useEffect(() => {
    if (!showEnterHint) return;

    const onFocusIn = (event: FocusEvent) => {
      const target = event.target;
      if (target instanceof Node && buttonRef.current?.contains(target)) return;
      setShowEnterHint(false);
    };

    document.addEventListener("focusin", onFocusIn);
    return () => document.removeEventListener("focusin", onFocusIn);
  }, [showEnterHint]);

  const handleButtonKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      if (event.key !== "Enter" || event.shiftKey) return;
      if (!canSaveRef.current) return;
      event.preventDefault();
      setShowEnterHint(false);
      onSaveRef.current();
    },
    [],
  );

  const onEditorMount = useCallback(
    (editorInstance: editor.IStandaloneCodeEditor, monaco: typeof Monaco) => {
      editorInstanceRef.current = editorInstance;
      monacoRef.current = monaco;
      installShortcut();
    },
    [installShortcut],
  );

  useEffect(() => {
    installShortcut();
    return () => {
      shortcutDisposableRef.current?.dispose();
      shortcutDisposableRef.current = null;
    };
  }, [installShortcut]);

  return {
    buttonRef,
    showEnterHint,
    enterHint: ENTER_TO_SAVE_HINT,
    handleButtonKeyDown,
    onEditorMount,
  };
}
