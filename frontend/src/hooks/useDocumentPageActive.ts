import { useEffect, useState } from "react";

function readPageActive(): boolean {
  if (typeof document === "undefined") return true;
  return document.visibilityState === "visible";
}

/** True while the browser tab/window is visible (Page Visibility API). */
export function useDocumentPageActive(): boolean {
  const [active, setActive] = useState(readPageActive);

  useEffect(() => {
    const onChange = () => setActive(readPageActive());
    document.addEventListener("visibilitychange", onChange);
    return () => document.removeEventListener("visibilitychange", onChange);
  }, []);

  return active;
}
