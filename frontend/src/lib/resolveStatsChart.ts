const MINUTE_MS = 60 * 1000
const HOUR_MS = 60 * MINUTE_MS
const DAY_MS = 24 * HOUR_MS

export const RESOLVE_BUCKET_MS = [
  30 * MINUTE_MS,
  HOUR_MS,
  2 * HOUR_MS,
  4 * HOUR_MS,
  12 * HOUR_MS,
  DAY_MS,
] as const

export const DEFAULT_RESOLVE_RANGE_MS = 30 * DAY_MS

/** Pick bucket size from visible range duration (see product thresholds). */
export function pickResolveBucketMs(rangeMs: number): number {
  if (rangeMs > 15 * DAY_MS) return DAY_MS
  if (rangeMs > 5 * DAY_MS) return 12 * HOUR_MS
  if (rangeMs > 3 * DAY_MS) return 4 * HOUR_MS
  if (rangeMs > 1 * DAY_MS) return 2 * HOUR_MS
  if (rangeMs >= 0.5 * DAY_MS) return HOUR_MS
  return 30 * MINUTE_MS
}

export function bucketSecondsFromMs(bucketMs: number): number {
  return Math.round(bucketMs / 1000)
}
