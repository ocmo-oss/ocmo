import { createPortal } from "react-dom";
import { cn } from "../../ui/cn";
import { FOCUS_TRANSITION_MS } from "./constants";

const BACKDROP_TRANSITION = `opacity ${FOCUS_TRANSITION_MS}ms ease-in-out, background-color ${FOCUS_TRANSITION_MS}ms ease-in-out, backdrop-filter ${FOCUS_TRANSITION_MS}ms ease-in-out, -webkit-backdrop-filter ${FOCUS_TRANSITION_MS}ms ease-in-out`;

export function EditorFocusBackdrop({
  show,
  dimmed,
  onClose,
}: {
  show: boolean;
  dimmed: boolean;
  onClose: () => void;
}) {
  if (!show) return null;

  return createPortal(
    <button
      type="button"
      aria-label="Exit focus mode"
      className={cn(
        "fixed inset-0 z-[45] border-0 p-0",
        dimmed ? "cursor-default" : "pointer-events-none",
      )}
      style={{
        transition: BACKDROP_TRANSITION,
        opacity: dimmed ? 1 : 0,
        backgroundColor: dimmed ? "rgba(0, 0, 0, 0.5)" : "rgba(0, 0, 0, 0)",
        backdropFilter: dimmed ? "blur(40px) saturate(1.5)" : "blur(0px)",
        WebkitBackdropFilter: dimmed ? "blur(40px) saturate(1.5)" : "blur(0px)",
      }}
      onClick={onClose}
    />,
    document.body,
  );
}
