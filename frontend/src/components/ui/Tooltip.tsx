import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "./cn";

type TooltipSide = "top" | "bottom" | "left" | "right";
type TooltipAlign = "start" | "center" | "end";

const GAP = 6;

function computePosition(
  rect: DOMRect,
  side: TooltipSide,
  align: TooltipAlign,
  tooltipWidth: number,
  tooltipHeight: number,
): { top: number; left: number } {
  let top = 0;
  let left = 0;

  if (side === "top") {
    top = rect.top - tooltipHeight - GAP;
    if (align === "start") left = rect.left;
    else if (align === "end") left = rect.right - tooltipWidth;
    else left = rect.left + rect.width / 2 - tooltipWidth / 2;
  } else if (side === "bottom") {
    top = rect.bottom + GAP;
    if (align === "start") left = rect.left;
    else if (align === "end") left = rect.right - tooltipWidth;
    else left = rect.left + rect.width / 2 - tooltipWidth / 2;
  } else if (side === "left") {
    left = rect.left - tooltipWidth - GAP;
    if (align === "start") top = rect.top;
    else if (align === "end") top = rect.bottom - tooltipHeight;
    else top = rect.top + rect.height / 2 - tooltipHeight / 2;
  } else {
    left = rect.right + GAP;
    if (align === "start") top = rect.top;
    else if (align === "end") top = rect.bottom - tooltipHeight;
    else top = rect.top + rect.height / 2 - tooltipHeight / 2;
  }

  const margin = 8;
  const maxLeft = window.innerWidth - tooltipWidth - margin;
  const maxTop = window.innerHeight - tooltipHeight - margin;
  left = Math.min(Math.max(left, margin), maxLeft);
  top = Math.min(Math.max(top, margin), maxTop);

  return { top, left };
}

export function Tooltip({
  content,
  children,
  className,
  side = "top",
  align = "center",
  open,
  showOnHover = true,
}: {
  content: ReactNode;
  children: ReactNode;
  className?: string;
  side?: TooltipSide;
  align?: TooltipAlign;
  /** When true, force the tooltip visible (e.g. keyboard shortcut hint). */
  open?: boolean;
  /** When false, the tooltip is only shown while `open` is true. */
  showOnHover?: boolean;
}) {
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLSpanElement>(null);
  const [hovered, setHovered] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(
    null,
  );

  const visible = open === true || (showOnHover && hovered && open !== false);

  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current;
    const tooltip = tooltipRef.current;
    if (!trigger || !tooltip) return;
    const rect = trigger.getBoundingClientRect();
    setCoords(
      computePosition(
        rect,
        side,
        align,
        tooltip.offsetWidth,
        tooltip.offsetHeight,
      ),
    );
  }, [side, align]);

  useLayoutEffect(() => {
    if (!visible) {
      setCoords(null);
      return;
    }
    updatePosition();
    const raf = requestAnimationFrame(updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [visible, updatePosition, content]);

  return (
    <span
      ref={triggerRef}
      className={cn("relative inline-flex", className)}
      onMouseEnter={showOnHover ? () => setHovered(true) : undefined}
      onMouseLeave={showOnHover ? () => setHovered(false) : undefined}
    >
      {children}
      {visible &&
        createPortal(
          <span
            ref={tooltipRef}
            role="tooltip"
            className={cn(
              "pointer-events-none fixed z-[10000] w-max max-w-xs rounded border bg-surface-elevated px-2 py-1.5 text-[11px] leading-snug text-gray-600 shadow-lg",
              "dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300",
              coords ? "opacity-100" : "opacity-0",
            )}
            style={
              coords
                ? { top: coords.top, left: coords.left }
                : { top: -9999, left: -9999 }
            }
          >
            {content}
          </span>,
          document.body,
        )}
    </span>
  );
}
