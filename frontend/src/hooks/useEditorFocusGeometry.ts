import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import {
  FOCUS_TRANSITION_MS,
  focusIdleRect,
  focusResolveRect,
  prefersReducedMotion,
} from "../components/editor/focus/constants";

type PanelPhase = "inline" | "entering" | "open" | "exiting";

function isFocusPanelPhase(phase: PanelPhase): boolean {
  return phase === "entering" || phase === "open" || phase === "exiting";
}

export function useEditorFocusGeometry({
  focusOpen,
  resolveSplitOpen,
  anchorRef,
}: {
  focusOpen: boolean;
  resolveSplitOpen: boolean;
  anchorRef: RefObject<HTMLElement | null>;
}) {
  const [phase, setPhase] = useState<PanelPhase>("inline");
  const [panelStyle, setPanelStyle] = useState<CSSProperties>({});
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  const targetRect = useCallback(() => {
    return resolveSplitOpen ? focusResolveRect() : focusIdleRect();
  }, [resolveSplitOpen]);

  const applyRect = useCallback(
    (rect: { top: number; left: number; width: number; height: number }) => {
      setPanelStyle({
        position: "fixed",
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
        zIndex: 46,
      });
    },
    [],
  );

  useLayoutEffect(() => {
    const reduced = prefersReducedMotion();

    if (focusOpen) {
      if (phaseRef.current === "inline" || phaseRef.current === "exiting") {
        const anchor = anchorRef.current?.getBoundingClientRect();
        if (!anchor || reduced) {
          applyRect(targetRect());
          setPhase("open");
          return;
        }
        applyRect({
          top: anchor.top,
          left: anchor.left,
          width: anchor.width,
          height: anchor.height,
        });
        setPhase("entering");
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            applyRect(targetRect());
            setPhase("open");
          });
        });
      }
      return;
    }

    if (!focusOpen && phaseRef.current === "open") {
      const anchor = anchorRef.current?.getBoundingClientRect();
      if (!anchor || reduced) {
        setPanelStyle({});
        setPhase("inline");
        return;
      }
      setPhase("exiting");
      applyRect(targetRect());
      requestAnimationFrame(() => {
        applyRect({
          top: anchor.top,
          left: anchor.left,
          width: anchor.width,
          height: anchor.height,
        });
      });
      const t = window.setTimeout(() => {
        setPanelStyle({});
        setPhase("inline");
      }, FOCUS_TRANSITION_MS + 50);
      return () => window.clearTimeout(t);
    }
  }, [focusOpen, anchorRef, applyRect, targetRect]);

  useLayoutEffect(() => {
    if (!focusOpen || phase !== "open") return;
    applyRect(targetRect());
  }, [resolveSplitOpen, focusOpen, phase, applyRect, targetRect]);

  const isFocusActive = focusOpen || isFocusPanelPhase(phase);

  const transitionStyle: CSSProperties =
    isFocusActive && !prefersReducedMotion()
      ? {
          transition: `top ${FOCUS_TRANSITION_MS}ms ease-in-out, left ${FOCUS_TRANSITION_MS}ms ease-in-out, width ${FOCUS_TRANSITION_MS}ms ease-in-out, height ${FOCUS_TRANSITION_MS}ms ease-in-out`,
        }
      : {};

  const backdropShow =
    phase === "entering" || phase === "open" || phase === "exiting";
  /** Full blur/dim while open; eases down in parallel with panel on exit. */
  const backdropDimmed = phase === "open" || phase === "entering";

  return {
    isFocusActive,
    backdropShow,
    backdropDimmed,
    panelStyle: isFocusActive ? { ...panelStyle, ...transitionStyle } : {},
    phase,
  };
}
