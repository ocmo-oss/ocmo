import { useCallback, useEffect, useRef, useState } from "react";
import { useTheme } from "../../store/theme";
import {
  STITCH_MS,
  buildBandCells,
  drawCell,
  readBandColors,
  scheduleCells,
} from "./embroidery";
import { layoutSizeChanged, waitForLayoutReady } from "./embroideryLayout";
import type { BandCell, StitchData } from "./types";

interface SectionRefs {
  top: HTMLDivElement | null;
  message: HTMLElement | null;
  bottom: HTMLDivElement | null;
}

export function useBandEmbroidery(
  bandRef: React.RefObject<HTMLElement | null>,
  data: StitchData,
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sectionRefs = useRef<SectionRefs>({
    top: null,
    message: null,
    bottom: null,
  });
  const scheduleRef = useRef<BandCell[]>([]);
  const indexRef = useRef(0);
  const frameRef = useRef(0);
  const startedRef = useRef(0);
  const messageTriggeredRef = useRef(false);
  const colorsRef = useRef(readBandColors(document.documentElement));
  const sizeRef = useRef({ w: 0, h: 0 });
  const layoutSizeRef = useRef({ w: 0, h: 0 });
  const completeRef = useRef(false);
  const { theme } = useTheme();
  const [playing, setPlaying] = useState(false);
  const [complete, setComplete] = useState(false);

  const setSectionRef = useCallback(
    (key: keyof SectionRefs) => (node: HTMLDivElement | HTMLElement | null) => {
      sectionRefs.current[key] = node as never;
    },
    [],
  );

  const isLayoutReady = useCallback(() => {
    const band = bandRef.current;
    const { top, message, bottom } = sectionRefs.current;
    if (!band || !top || !message || !bottom) return false;

    const bandH = band.clientHeight;
    const bandW = band.clientWidth;
    if (bandW < 1 || bandH < 50) return false;

    const sum = top.clientHeight + message.clientHeight + bottom.clientHeight;
    return Math.abs(sum - bandH) <= 2;
  }, [bandRef]);

  const triggerMessage = useCallback((instant: boolean) => {
    if (messageTriggeredRef.current) return;
    messageTriggeredRef.current = true;
    setPlaying(true);
    if (instant) {
      completeRef.current = true;
      setComplete(true);
    }
  }, []);

  const paint = useCallback(
    (elapsed: number, reduced: boolean) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const { cell } = data;
      const colors = colorsRef.current;
      const schedule = scheduleRef.current;

      if (reduced) {
        for (const item of schedule) {
          drawCell(ctx, item, cell, colors);
        }
        indexRef.current = schedule.length;
        triggerMessage(true);
        return;
      }

      while (
        indexRef.current < schedule.length &&
        (schedule[indexRef.current].t ?? 0) <= elapsed
      ) {
        const item = schedule[indexRef.current];
        if (
          !messageTriggeredRef.current &&
          (item.kind === "message" ||
            item.kind === "accent-top" ||
            item.kind === "accent-bottom" ||
            item.kind === "hem-dash")
        ) {
          triggerMessage(false);
        }
        drawCell(ctx, item, cell, colors);
        indexRef.current += 1;
      }

      if (indexRef.current >= schedule.length) {
        completeRef.current = true;
        setComplete(true);
      }
    },
    [data, triggerMessage],
  );

  const buildSchedule = useCallback(() => {
    const band = bandRef.current;
    const { top, message, bottom } = sectionRefs.current;
    if (!band || !top || !message || !bottom || !isLayoutReady()) return false;

    const w = band.clientWidth;
    const topH = top.clientHeight;
    const msgTop = topH;
    const msgH = message.clientHeight;
    const bottomTop = topH + msgH;
    const bottomH = bottom.clientHeight;
    const totalH = topH + msgH + bottomH;

    const messageFontSize =
      parseFloat(getComputedStyle(message).fontSize) || 12;
    colorsRef.current = readBandColors(band);
    const cells = buildBandCells(
      data,
      { width: w, topH, msgTop, msgH, bottomTop, bottomH, totalH },
      messageFontSize,
    );
    scheduleRef.current = scheduleCells(cells, data.cell, 0);
    return true;
  }, [bandRef, data, isLayoutReady]);

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

  const start = useCallback(() => {
    const band = bandRef.current;
    const canvas = canvasRef.current;
    if (!band || !canvas || !isLayoutReady()) return;
    if (!layoutCanvas() || !buildSchedule()) return;

    layoutSizeRef.current = { w: band.clientWidth, h: band.clientHeight };

    if (frameRef.current) cancelAnimationFrame(frameRef.current);

    const ctx = canvas.getContext("2d");
    ctx?.clearRect(0, 0, sizeRef.current.w, sizeRef.current.h);

    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    startedRef.current = performance.now();
    indexRef.current = 0;
    messageTriggeredRef.current = false;
    completeRef.current = false;
    setPlaying(false);
    setComplete(false);

    const tick = (now: number) => {
      const elapsed = now - startedRef.current;
      paint(elapsed, reduced);

      if (!reduced && indexRef.current < scheduleRef.current.length) {
        frameRef.current = requestAnimationFrame(tick);
      } else {
        frameRef.current = 0;
        if (!messageTriggeredRef.current) triggerMessage(reduced);
      }
    };

    frameRef.current = requestAnimationFrame(tick);
  }, [buildSchedule, isLayoutReady, layoutCanvas, paint, triggerMessage]);

  const repaintComplete = useCallback(() => {
    if (!layoutCanvas() || !buildSchedule()) return;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    ctx?.clearRect(0, 0, sizeRef.current.w, sizeRef.current.h);
    paint(Number.MAX_SAFE_INTEGER, true);
    setPlaying(true);
    setComplete(true);
    completeRef.current = true;
    messageTriggeredRef.current = true;
  }, [buildSchedule, layoutCanvas, paint]);

  const handleResize = useCallback(() => {
    const band = bandRef.current;
    if (!band || !isLayoutReady()) return;

    const w = band.clientWidth;
    const h = band.clientHeight;
    if (!layoutSizeChanged(layoutSizeRef.current, w, h)) return;

    layoutSizeRef.current = { w, h };

    if (completeRef.current) {
      repaintComplete();
      return;
    }

    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    start();
  }, [isLayoutReady, repaintComplete, start]);

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
    const cancelWait = waitForLayoutReady(isLayoutReady, start);
    return () => {
      cancelWait();
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [isLayoutReady, start, theme]);

  return {
    canvasRef,
    setTopRef: setSectionRef("top"),
    setMessageRef: setSectionRef("message"),
    setBottomRef: setSectionRef("bottom"),
    playing,
    complete,
    stitchEndMs: () => {
      const schedule = scheduleRef.current;
      if (!schedule.length) return STITCH_MS;
      return (schedule[schedule.length - 1].t ?? 0) + STITCH_MS;
    },
  };
}
