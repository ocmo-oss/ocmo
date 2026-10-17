export const FOCUS_TRANSITION_MS = 300;

function focusViewportHeight(): number {
  return window.innerHeight;
}

export function focusIdleRect(): {
  top: number;
  left: number;
  width: number;
  height: number;
} {
  const height = focusViewportHeight();
  const width = window.innerWidth * 0.5;
  const left = (window.innerWidth - width) / 2;
  return {
    top: 0,
    left,
    width,
    height,
  };
}

export function focusResolveRect(): {
  top: number;
  left: number;
  width: number;
  height: number;
} {
  return {
    top: 0,
    left: 0,
    width: window.innerWidth,
    height: focusViewportHeight(),
  };
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
