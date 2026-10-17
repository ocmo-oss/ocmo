import { useCallback, useState } from "react";

export function useEditorFocusMode() {
  const [focusOpen, setFocusOpen] = useState(false);
  const [resolveSplitOpen, setResolveSplitOpen] = useState(false);

  const openFocus = useCallback(() => setFocusOpen(true), []);
  const closeFocus = useCallback(() => {
    setFocusOpen(false);
    setResolveSplitOpen(false);
  }, []);

  const toggleResolveSplit = useCallback(() => {
    setResolveSplitOpen((o) => !o);
  }, []);

  return {
    focusOpen,
    resolveSplitOpen,
    openFocus,
    closeFocus,
    setFocusOpen,
    setResolveSplitOpen,
    toggleResolveSplit,
  };
}
