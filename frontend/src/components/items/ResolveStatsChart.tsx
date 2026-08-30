import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "../../api/audit";
import type { ItemType } from "../../api/types";
import {
  formatUserDateTime,
  formatUserDateTimeAxis,
  formatUserDateTimeBucketRange,
} from "../../lib/datetime";
import {
  bucketSecondsFromMs,
  DEFAULT_RESOLVE_RANGE_MS,
  pickResolveBucketMs,
} from "../../lib/resolveStatsChart";
import { Skeleton } from "../ui/Skeleton";
import { cn } from "../ui/cn";

const CHART_HEIGHT = 88;
const PAD_LEFT = 8;
const PAD_RIGHT = 8;
const PAD_TOP = 6;
const PAD_BOTTOM = 20;

interface ResolveStatsChartProps {
  namespace: string;
  path: string;
  type: ItemType;
}

function formatBucketLabel(iso: string, bucketMs: number): string {
  return formatUserDateTimeAxis(iso, bucketMs);
}

function formatBucketTooltip(iso: string, bucketMs: number): string {
  return formatUserDateTimeBucketRange(iso, bucketMs);
}

function bucketIndexFromX(x: number, count: number, width: number): number {
  if (count <= 0) return 0;
  if (count === 1) return 0;
  const stepX = width / (count - 1);
  return Math.max(0, Math.min(count - 1, Math.round(x / stepX)));
}

function bucketX(index: number, count: number, width: number): number {
  if (count <= 1) return width / 2;
  return (index / (count - 1)) * width;
}

function resolveTooltipPosition(
  anchorX: number,
  containerWidth: number,
  tooltipWidth: number,
  margin = 8,
): { left: number; transform: string } {
  const half = Math.max(tooltipWidth / 2, 1);

  if (anchorX - half < margin) {
    return { left: margin, transform: "translateX(0)" };
  }
  if (anchorX + half > containerWidth - margin) {
    return { left: containerWidth - margin, transform: "translateX(-100%)" };
  }
  return { left: anchorX, transform: "translateX(-50%)" };
}

function linePath(
  values: number[],
  width: number,
  height: number,
  max: number,
): string {
  if (values.length === 0 || width <= 0) return "";
  const stepX = values.length > 1 ? width / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = index * stepX;
      const y = max > 0 ? height - (value / max) * height : height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export function ResolveStatsChart({
  namespace,
  path,
  type,
}: ResolveStatsChartProps) {
  const showNested = type !== "resolver";
  const [rangeEnd, setRangeEnd] = useState(() => Date.now());
  const [rangeMs, setRangeMs] = useState(DEFAULT_RESOLVE_RANGE_MS);
  const [brush, setBrush] = useState<{ startX: number; endX: number } | null>(
    null,
  );
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [plotWidth, setPlotWidth] = useState(0);
  const [containerWidth, setContainerWidth] = useState(0);
  const [tooltipWidth, setTooltipWidth] = useState(0);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const brushRef = useRef<{ startX: number; endX: number } | null>(null);
  const isBrushingRef = useRef(false);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  const rangeStart = rangeEnd - rangeMs;
  const bucketMs = pickResolveBucketMs(rangeMs);
  const bucketSeconds = bucketSecondsFromMs(bucketMs);

  const plotRef = useCallback((node: HTMLDivElement | null) => {
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    if (!node) return;

    const update = () => {
      const width = Math.max(0, node.clientWidth);
      setContainerWidth(width);
      setPlotWidth(Math.max(0, width - PAD_LEFT - PAD_RIGHT));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    resizeObserverRef.current = observer;
  }, []);

  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: [
      "audit-resolve-series",
      namespace,
      path,
      type,
      rangeStart,
      rangeEnd,
      bucketSeconds,
    ],
    queryFn: ({ signal }) =>
      auditApi.getResolveSeries(
        namespace,
        {
          object_id: path,
          object_type: type,
          from: new Date(rangeStart).toISOString(),
          to: new Date(rangeEnd).toISOString(),
          bucket_seconds: bucketSeconds,
        },
        signal,
      ),
    staleTime: 30_000,
    refetchOnMount: "always",
  });

  const buckets = data?.buckets ?? [];
  const directValues = buckets.map((bucket) => bucket.direct);
  const nestedValues = buckets.map((bucket) => bucket.nested);
  const errorValues = buckets.map((bucket) => bucket.errors ?? 0);
  const maxValue = Math.max(
    1,
    ...directValues,
    ...nestedValues,
    ...errorValues,
  );
  const hasActivity =
    directValues.some((v) => v > 0) ||
    nestedValues.some((v) => v > 0) ||
    errorValues.some((v) => v > 0);

  const totals = useMemo(
    () => ({
      direct: directValues.reduce((sum, value) => sum + value, 0),
      nested: nestedValues.reduce((sum, value) => sum + value, 0),
      errors: errorValues.reduce((sum, value) => sum + value, 0),
    }),
    [directValues, errorValues, nestedValues],
  );

  const resetRange = useCallback(() => {
    setRangeEnd(Date.now());
    setRangeMs(DEFAULT_RESOLVE_RANGE_MS);
    brushRef.current = null;
    setBrush(null);
  }, []);

  const finishBrush = useCallback(
    (startX: number, endX: number) => {
      if (plotWidth <= 0) return;
      const minPx = Math.max(0, Math.min(startX, endX));
      const maxPx = Math.min(plotWidth, Math.max(startX, endX));
      if (maxPx - minPx < 12) return;

      const startTime = rangeStart + (minPx / plotWidth) * rangeMs;
      const endTime = rangeStart + (maxPx / plotWidth) * rangeMs;
      setRangeEnd(endTime);
      setRangeMs(Math.max(endTime - startTime, 30 * 60 * 1000));
    },
    [plotWidth, rangeMs, rangeStart],
  );

  const plotX = (clientX: number, rect: DOMRect) =>
    clientX - rect.left - PAD_LEFT;

  const updateHover = (x: number) => {
    if (buckets.length === 0) {
      setHoverIndex(null);
      return;
    }
    setHoverIndex(bucketIndexFromX(x, buckets.length, plotWidth));
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    isBrushingRef.current = true;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = plotX(event.clientX, rect);
    const next = { startX: x, endX: x };
    brushRef.current = next;
    setBrush(next);
    setHoverIndex(null);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = plotX(event.clientX, rect);

    if (isBrushingRef.current && brushRef.current) {
      const next = { ...brushRef.current, endX: x };
      brushRef.current = next;
      setBrush(next);
      return;
    }

    updateHover(x);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    isBrushingRef.current = false;
    const current = brushRef.current;
    if (current) {
      const rect = event.currentTarget.getBoundingClientRect();
      const x = plotX(event.clientX, rect);
      finishBrush(current.startX, x);
      brushRef.current = null;
      setBrush(null);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    updateHover(
      plotX(event.clientX, event.currentTarget.getBoundingClientRect()),
    );
  };

  const onPointerLeave = () => {
    if (!isBrushingRef.current) setHoverIndex(null);
  };

  const rangeLabel = `${formatUserDateTime(rangeStart)} – ${formatUserDateTime(rangeEnd)}`;
  const innerWidth = Math.max(plotWidth, 1);
  const svgHeight = CHART_HEIGHT + PAD_TOP + PAD_BOTTOM;
  const hoveredBucket = hoverIndex !== null ? buckets[hoverIndex] : null;
  const hoverX =
    hoverIndex !== null
      ? bucketX(hoverIndex, buckets.length, innerWidth)
      : null;
  const tooltipAnchorX = hoverX !== null ? PAD_LEFT + hoverX : 0;
  const tooltipPosition =
    hoverX !== null && containerWidth > 0
      ? resolveTooltipPosition(
          tooltipAnchorX,
          containerWidth,
          tooltipWidth || 180,
        )
      : null;

  useLayoutEffect(() => {
    if (!hoveredBucket || !tooltipRef.current) {
      setTooltipWidth(0);
      return;
    }
    setTooltipWidth(tooltipRef.current.offsetWidth);
  }, [hoveredBucket, hoverIndex, type, showNested, bucketMs]);

  return (
    <div className="shrink-0 border-b px-4 py-2 dark:border-gray-700">
      <div className="mb-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-500">
        <span className="font-medium text-gray-600 dark:text-gray-300">
          Resolves
        </span>
        <span>{rangeLabel}</span>
        <span className="inline-flex items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-brand-500" />
            {type === "resolver" ? "Resolves" : "Direct"} {totals.direct}
          </span>
          {showNested && (
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              Nested {totals.nested}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            Errors {totals.errors}
          </span>
        </span>
        {rangeMs < DEFAULT_RESOLVE_RANGE_MS && (
          <button
            type="button"
            className="text-brand-600 hover:underline dark:text-brand-400"
            onClick={resetRange}
          >
            Last 30 days
          </button>
        )}
        {isFetching && !isLoading && (
          <span className="text-gray-400">Updating…</span>
        )}
      </div>

      <div
        ref={plotRef}
        className={cn(
          "relative w-full cursor-crosshair select-none touch-none rounded-md",
          "bg-surface ring-1 ring-gray-200/80 dark:bg-gray-800/50 dark:ring-gray-700/60",
          isLoading && "opacity-60",
        )}
        style={{ height: svgHeight }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onPointerLeave={onPointerLeave}
        onDoubleClick={resetRange}
        title="Drag to zoom a range; double-click to reset"
      >
        {isLoading && (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
            <Skeleton className="h-full w-full" />
          </div>
        )}

        {isError && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-xs text-red-500">
            Failed to load resolve chart
          </div>
        )}

        <svg
          width="100%"
          height={svgHeight}
          viewBox={`0 0 ${innerWidth + PAD_LEFT + PAD_RIGHT} ${svgHeight}`}
          preserveAspectRatio="none"
          className="block"
        >
          <g transform={`translate(${PAD_LEFT}, ${PAD_TOP})`}>
            {[0, 0.5, 1].map((ratio) => (
              <line
                key={ratio}
                x1={0}
                x2={innerWidth}
                y1={CHART_HEIGHT * ratio}
                y2={CHART_HEIGHT * ratio}
                className="stroke-gray-200/90 dark:stroke-gray-600/80"
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
              />
            ))}
            <path
              d={linePath(errorValues, innerWidth, CHART_HEIGHT, maxValue)}
              fill="none"
              className="stroke-red-500"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
            <path
              d={linePath(nestedValues, innerWidth, CHART_HEIGHT, maxValue)}
              fill="none"
              className="stroke-amber-500"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              style={{ display: showNested ? undefined : "none" }}
            />
            <path
              d={linePath(directValues, innerWidth, CHART_HEIGHT, maxValue)}
              fill="none"
              className="stroke-brand-500"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
            />
            {brush && (
              <rect
                x={Math.min(brush.startX, brush.endX)}
                y={0}
                width={Math.max(1, Math.abs(brush.endX - brush.startX))}
                height={CHART_HEIGHT}
                className="fill-brand-500/15 stroke-brand-500/70"
                strokeWidth={1}
                vectorEffect="non-scaling-stroke"
              />
            )}
            {hoverX !== null && !brush && (
              <>
                <line
                  x1={hoverX}
                  x2={hoverX}
                  y1={0}
                  y2={CHART_HEIGHT}
                  className="stroke-gray-400 dark:stroke-gray-500"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  vectorEffect="non-scaling-stroke"
                />
                {hoverIndex !== null && (
                  <>
                    <circle
                      cx={hoverX}
                      cy={
                        CHART_HEIGHT -
                        (errorValues[hoverIndex] / maxValue) * CHART_HEIGHT
                      }
                      r={3}
                      className="fill-red-500 stroke-white dark:stroke-gray-900"
                      strokeWidth={1}
                      vectorEffect="non-scaling-stroke"
                    />
                    <circle
                      cx={hoverX}
                      cy={
                        CHART_HEIGHT -
                        (nestedValues[hoverIndex] / maxValue) * CHART_HEIGHT
                      }
                      r={3}
                      className="fill-amber-500 stroke-white dark:stroke-gray-900"
                      strokeWidth={1}
                      vectorEffect="non-scaling-stroke"
                      style={{ display: showNested ? undefined : "none" }}
                    />
                    <circle
                      cx={hoverX}
                      cy={
                        CHART_HEIGHT -
                        (directValues[hoverIndex] / maxValue) * CHART_HEIGHT
                      }
                      r={3}
                      className="fill-brand-500 stroke-white dark:stroke-gray-900"
                      strokeWidth={1}
                      vectorEffect="non-scaling-stroke"
                    />
                  </>
                )}
              </>
            )}
          </g>
        </svg>

        {hoveredBucket && hoverX !== null && tooltipPosition && !brush && (
          <div
            ref={tooltipRef}
            className="pointer-events-none absolute top-1 z-20 rounded border border-slate-300 bg-surface-elevated px-2 py-1 text-[10px] shadow-md dark:border-gray-600 dark:bg-gray-800"
            style={{
              left: tooltipPosition.left,
              transform: tooltipPosition.transform,
            }}
          >
            <div className="whitespace-nowrap font-medium text-gray-700 dark:text-gray-200">
              {formatBucketTooltip(hoveredBucket.start, bucketMs)}
            </div>
            <div className="mt-0.5 flex gap-2 whitespace-nowrap text-gray-600 dark:text-gray-300">
              <span className="text-brand-600 dark:text-brand-400">
                {type === "resolver" ? "Resolves" : "Direct"}{" "}
                {hoveredBucket.direct}
              </span>
              {showNested && (
                <span className="text-amber-600 dark:text-amber-400">
                  Nested {hoveredBucket.nested}
                </span>
              )}
              <span className="text-red-600 dark:text-red-400">
                Errors {hoveredBucket.errors ?? 0}
              </span>
            </div>
          </div>
        )}

        {!isLoading && buckets.length > 0 && (
          <div className="pointer-events-none absolute bottom-0 left-0 right-0 flex justify-between px-2 text-[10px] text-gray-400">
            <span>{formatBucketLabel(buckets[0].start, bucketMs)}</span>
            <span>
              {formatBucketLabel(buckets[buckets.length - 1].start, bucketMs)}
            </span>
          </div>
        )}

        {!isLoading && !isError && buckets.length > 0 && !hasActivity && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center pt-2 text-xs text-gray-400">
            No resolve activity in this range
          </div>
        )}
      </div>

      <p className="mt-0.5 text-[10px] text-gray-400">
        Drag on chart to zoom · double-click to reset
      </p>
    </div>
  );
}
