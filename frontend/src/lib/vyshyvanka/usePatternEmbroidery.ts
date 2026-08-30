import { useCallback, useEffect, useRef } from "react";
import { useTheme } from "../../store/theme";
import {
  RESOLVE_TIMING,
  buildPatternOnlyCells,
  drawCell,
  readBandColors,
  scheduleCells,
} from "./embroidery";
import type { EmbroideryTiming } from "./embroidery";
import { layoutSizeChanged, waitForLayoutReady } from "./embroideryLayout";
import type { BandCell, StitchData } from "./types";

interface UsePatternEmbroideryOptions {
  active: boolean;
  timing?: EmbroideryTiming;
}

export function usePatternEmbroidery(
  bandRef: React.RefObject<HTMLElement | null>,
  data: StitchData,
  { active, timing = RESOLVE_TIMING }: UsePatternEmbroideryOptions,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const scheduleRef = useRef<BandCell[]>([]);
  const indexRef = useRef(0);
  const frameRef = useRef(0);
  const startedRef = useRef(0);
  const activeRef = useRef(active);
  const colorsRef = useRef(readBandColors(document.documentElement));
  const sizeRef = useRef({ w: 0, h: 0 });
  const layoutSizeRef = useRef({ w: 0, h: 0 });
  const runCycleRef = useRef<() => void>(() => {});
  const { theme } = useTheme();

  activeRef.current = active;

  const clearCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, sizeRef.current.w, sizeRef.current.h);
  }, []);

  const layoutCanvas = useCallback(() => {
    const band = bandRef.current;
    const canvas = canvasRef.current;
    if (!band || !canvas) return false;

    const dpr = window.devicePixelRatio || 1;
    const w = band.clientWidth;
    const h = band.clientHeight;
    if (!w || !h) return false;

    canvas.width = Math.max(1, Math.floor(w * dpr));
    canvas.height = Math.max(1, Math.floor(h * dpr));
    const ctx = canvas.getContext("2d");
    ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
    sizeRef.current = { w, h };
    return true;
  }, [bandRef]);

  const buildSchedule = useCallback(() => {
    const band = bandRef.current;
    if (!band) return false;

    const w = band.clientWidth;
    const h = band.clientHeight;
    if (w < 1 || h < 50) return false;

    colorsRef.current = readBandColors(band);
    const cells = buildPatternOnlyCells(data, w, h);
    scheduleRef.current = scheduleCells(cells, data.cell, 0, timing);
    return true;
  }, [bandRef, data, timing]);

  const paintFrame = useCallback(
    (elapsed: number, reduced: boolean) => {
      const canvas = canvasRef.current;
      if (!canvas) return false;

      const ctx = canvas.getContext("2d");
      if (!ctx) return false;

      const { cell } = data;
      const colors = colorsRef.current;
      const schedule = scheduleRef.current;

      if (reduced) {
        for (const item of schedule) {
          drawCell(ctx, item, cell, colors);
        }
        indexRef.current = schedule.length;
        return true;
      }

      while (
        indexRef.current < schedule.length &&
        (schedule[indexRef.current].t ?? 0) <= elapsed
      ) {
        drawCell(ctx, schedule[indexRef.current], cell, colors);
        indexRef.current += 1;
      }

      return indexRef.current >= schedule.length;
    },
    [data],
  );

  const stop = useCallback(() => {
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = 0;
    }
    clearCanvas();
    indexRef.current = 0;
  }, [clearCanvas]);

  const runCycle = useCallback(() => {
    if (!activeRef.current) return;
    if (!layoutCanvas() || !buildSchedule()) return;

    const band = bandRef.current;
    if (band) {
      layoutSizeRef.current = { w: band.clientWidth, h: band.clientHeight };
    }

    clearCanvas();
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    startedRef.current = performance.now();
    indexRef.current = 0;

    const tick = (now: number) => {
      if (!activeRef.current) {
        stop();
        return;
      }

      const elapsed = now - startedRef.current;
      const done = paintFrame(elapsed, reduced);

      if (!activeRef.current) {
        stop();
        return;
      }

      if (!done && !reduced) {
        frameRef.current = requestAnimationFrame(tick);
        return;
      }

      frameRef.current = 0;
      if (activeRef.current && !reduced) {
        runCycleRef.current();
      }
    };

    if (reduced) {
      paintFrame(0, true);
      return;
    }

    frameRef.current = requestAnimationFrame(tick);
  }, [bandRef, buildSchedule, clearCanvas, layoutCanvas, paintFrame, stop]);

  runCycleRef.current = runCycle;

  const handleResize = useCallback(() => {
    if (!activeRef.current) return;

    const band = bandRef.current;
    if (!band) return;

    const w = band.clientWidth;
    const h = band.clientHeight;
    if (!layoutSizeChanged(layoutSizeRef.current, w, h)) return;

    layoutSizeRef.current = { w, h };
    stop();
    runCycleRef.current();
  }, [stop]);

  useEffect(() => {
    const band = bandRef.current;
    if (!band) return;

    const observer = new ResizeObserver(() => {
      requestAnimationFrame(handleResize);
    });
    observer.observe(band);
    return () => observer.disconnect();
  }, [handleResize]);

  useEffect(() => {
    if (!active) {
      stop();
      layoutSizeRef.current = { w: 0, h: 0 };
      return undefined;
    }

    const cancelWait = waitForLayoutReady(
      () => buildSchedule(),
      () => runCycleRef.current(),
    );
    return () => {
      cancelWait();
      stop();
    };
  }, [active, buildSchedule, stop, theme]);

  return { canvasRef };
}
