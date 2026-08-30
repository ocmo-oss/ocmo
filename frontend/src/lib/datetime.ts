import { format, formatDistanceToNow } from "date-fns";

export type UserDateTimeStyle = "default" | "short" | "long" | "date";

/** Browser IANA timezone used for all user-facing datetime display. */
export function getUserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export function parseApiDateTime(
  value: string | null | undefined,
): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function toDate(value: string | Date | number | null | undefined): Date | null {
  if (value instanceof Date)
    return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value === "number") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  return parseApiDateTime(value);
}

export function isSameCalendarYear(
  date: Date,
  reference: Date = new Date(),
): boolean {
  return date.getFullYear() === reference.getFullYear();
}

/** date-fns pattern for user-facing datetimes (24h clock, year when not current). */
export function userDateTimeFormatPattern(
  date: Date,
  style: UserDateTimeStyle = "default",
  reference: Date = new Date(),
): string {
  const sameYear = isSameCalendarYear(date, reference);

  switch (style) {
    case "short":
      return sameYear ? "MMM d HH:mm" : "MMM d, yyyy HH:mm";
    case "long":
      return sameYear ? "EEEE, MMMM d, HH:mm" : "EEEE, MMMM d, yyyy, HH:mm";
    case "date":
      return sameYear ? "MMM d" : "MMM d, yyyy";
    default:
      return sameYear ? "MMM d, HH:mm" : "MMM d, yyyy, HH:mm";
  }
}

/**
 * Format an API UTC timestamp for display in the user's local timezone.
 * Uses 24-hour time. Omits the year when it matches the current calendar year.
 */
export function formatUserDateTime(
  value: string | Date | number | null | undefined,
  style: UserDateTimeStyle = "default",
): string {
  const date = toDate(value);
  if (!date) return "—";
  return format(date, userDateTimeFormatPattern(date, style));
}

export function formatUserDateTimeShort(
  value: string | Date | number | null | undefined,
): string {
  return formatUserDateTime(value, "short");
}

export function formatUserDateTimeLong(
  value: string | Date | number | null | undefined,
): string {
  return formatUserDateTime(value, "long");
}

export function formatUserDateTimeRelative(
  value: string | Date | number | null | undefined,
): string {
  const date = toDate(value);
  if (!date) return "—";
  return formatDistanceToNow(date, { addSuffix: true });
}

/** Axis / bucket label for resolve charts and similar time-series UI. */
export function formatUserDateTimeAxis(
  value: string | Date | number,
  bucketMs: number,
  reference: Date = new Date(),
): string {
  const date = toDate(value);
  if (!date) return "—";
  const sameYear = isSameCalendarYear(date, reference);

  if (bucketMs >= 24 * 60 * 60 * 1000) {
    return format(date, sameYear ? "MMM d" : "MMM d, yyyy");
  }
  if (bucketMs >= 60 * 60 * 1000) {
    return format(date, sameYear ? "MMM d HH:mm" : "MMM d, yyyy HH:mm");
  }
  return format(date, "HH:mm");
}

/** Tooltip label for a chart bucket spanning [start, start + bucketMs). */
export function formatUserDateTimeBucketRange(
  start: string | Date | number,
  bucketMs: number,
  reference: Date = new Date(),
): string {
  const startDate = toDate(start);
  if (!startDate) return "—";
  const endDate = new Date(startDate.getTime() + bucketMs);
  const sameYear =
    isSameCalendarYear(startDate, reference) &&
    isSameCalendarYear(endDate, reference);

  if (bucketMs >= 24 * 60 * 60 * 1000) {
    return format(startDate, sameYear ? "MMM d" : "MMM d, yyyy");
  }

  const endOnSameDay =
    startDate.getFullYear() === endDate.getFullYear() &&
    startDate.getMonth() === endDate.getMonth() &&
    startDate.getDate() === endDate.getDate();

  const startPattern = sameYear ? "MMM d, HH:mm" : "MMM d, yyyy, HH:mm";
  if (endOnSameDay) {
    return `${format(startDate, startPattern)}-${format(endDate, "HH:mm")}`;
  }

  const endPattern = isSameCalendarYear(endDate, reference)
    ? "MMM d, HH:mm"
    : "MMM d, yyyy, HH:mm";
  return `${format(startDate, startPattern)}-${format(endDate, endPattern)}`;
}

/** Convert a `datetime-local` value (user wall time) to UTC ISO for the API. */
export function localDateTimeInputToUtcIso(
  localValue: string,
): string | undefined {
  const trimmed = localValue.trim();
  if (!trimmed) return undefined;
  const date = new Date(trimmed);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

/** Convert a UTC ISO timestamp from the API to a `datetime-local` input value. */
export function localDateTimeInputFromDate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function utcIsoToLocalDateTimeInput(
  iso: string | null | undefined,
): string {
  const date = parseApiDateTime(iso);
  if (!date) return "";
  return localDateTimeInputFromDate(date);
}

/** Minimum future offset for lock expiry (`datetime-local` input). */
export const LOCK_EXPIRES_MIN_OFFSET_MS = 30 * 60 * 1000;

/** Earliest allowed `datetime-local` value from now plus an offset. */
export function minFutureLocalDateTimeInput(
  offsetMs: number,
  now: Date = new Date(),
): string {
  return localDateTimeInputFromDate(new Date(now.getTime() + offsetMs));
}

/** True when empty (optional) or at/after `minDate` in local wall time. */
export function isOptionalFutureLocalDateTimeInput(
  localValue: string,
  minDate: Date,
): boolean {
  const trimmed = localValue.trim();
  if (!trimmed) return true;
  const date = new Date(trimmed);
  if (Number.isNaN(date.getTime())) return false;
  return date.getTime() >= minDate.getTime();
}
