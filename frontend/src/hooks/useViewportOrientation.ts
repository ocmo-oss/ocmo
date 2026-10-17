import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  window.addEventListener("resize", callback);
  const mq = window.matchMedia("(orientation: landscape)");
  mq.addEventListener("change", callback);
  return () => {
    window.removeEventListener("resize", callback);
    mq.removeEventListener("change", callback);
  };
}

export function isLandscapeDimensions(width: number, height: number): boolean {
  return width > height;
}

export function isViewportLandscape(): boolean {
  return isLandscapeDimensions(window.innerWidth, window.innerHeight);
}

function getSnapshot() {
  return isViewportLandscape();
}

function getServerSnapshot() {
  return true;
}

/** True when viewport width exceeds height (landscape layout for focus resolve split). */
export function useViewportOrientation(): { isLandscape: boolean } {
  const isLandscape = useSyncExternalStore(
    subscribe,
    getSnapshot,
    getServerSnapshot,
  );
  return { isLandscape };
}
