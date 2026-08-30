export interface LayoutSize {
  w: number;
  h: number;
}

export function layoutSizeChanged(
  prev: LayoutSize,
  w: number,
  h: number,
): boolean {
  return Math.abs(prev.w - w) > 1 || Math.abs(prev.h - h) > 1;
}

export function waitForLayoutReady(
  measure: () => boolean,
  onReady: () => void,
  maxAttempts = 40,
): () => void {
  let attempts = 0;
  let frameId = 0;
  let cancelled = false;

  const tick = () => {
    if (cancelled) return;
    if (measure() || attempts >= maxAttempts) {
      if (!cancelled && measure()) onReady();
      return;
    }
    attempts += 1;
    frameId = requestAnimationFrame(tick);
  };

  frameId = requestAnimationFrame(tick);

  return () => {
    cancelled = true;
    cancelAnimationFrame(frameId);
  };
}
