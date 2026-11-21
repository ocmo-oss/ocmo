import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from "react";
import type { editor } from "monaco-editor";
import type * as Monaco from "monaco-editor";
import { installEditorSaveShortcut } from "../lib/editorSaveShortcut";

const ENTER_TO_SAVE_HINT = "Press Enter to save";
export const ENTER_TO_CREATE_CR_HINT = "Press Enter to create change request";

export function useItemSaveShortcut({
  canSave,
  onSave,
  canFocusShortcut,
  focusButtonRef,
  enterHint: enterHintProp,
  onEnterKey,
}: {
  canSave: boolean;
  onSave: () => void;
  /** When false, Ctrl/Cmd+S does not move focus (defaults to canSave). */
  canFocusShortcut?: boolean;
  /** Button to focus on save shortcut (defaults to primary save ref). */
  focusButtonRef?: RefObject<HTMLButtonElement | null>;
  enterHint?: string;
  /** Enter on focused shortcut button when `canSave` is false. */
  onEnterKey?: () => void;
}) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [showEnterHint, setShowEnterHint] = useState(false);
  const canSaveRef = useRef(canSave);
  const canFocusRef = useRef(canFocusShortcut ?? canSave);
  const onSaveRef = useRef(onSave);
  const onEnterKeyRef = useRef(onEnterKey);
  const editorInstanceRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const monacoRef = useRef<typeof Monaco | null>(null);
  const shortcutDisposableRef = useRef<Monaco.IDisposable | null>(null);
  canSaveRef.current = canSave;
  canFocusRef.current = canFocusShortcut ?? canSave;
  onSaveRef.current = onSave;
  onEnterKeyRef.current = onEnterKey;

  const resolveFocusRef = () => focusButtonRef?.current ?? buttonRef.current;

  const focusSaveButton = useCallback(() => {
    if (!canFocusRef.current) return;
    setShowEnterHint(true);
    resolveFocusRef()?.focus({ preventScroll: true });
  }, [focusButtonRef]);

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
      const focusEl = resolveFocusRef();
      if (target instanceof Node && focusEl?.contains(target)) return;
      setShowEnterHint(false);
    };

    document.addEventListener("focusin", onFocusIn);
    return () => document.removeEventListener("focusin", onFocusIn);
  }, [showEnterHint]);

  const handleButtonKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>) => {
      if (event.key !== "Enter" || event.shiftKey) return;
      if (!canSaveRef.current && !onEnterKeyRef.current) return;
      event.preventDefault();
      setShowEnterHint(false);
      if (canSaveRef.current) {
        onSaveRef.current();
        return;
      }
      onEnterKeyRef.current?.();
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
    enterHint: enterHintProp ?? ENTER_TO_SAVE_HINT,
    handleButtonKeyDown,
    onEditorMount,
  };
}
