import {
  afterEach,
  beforeAll,
  afterAll,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import {
  formatUserDateTime,
  formatUserDateTimeAxis,
  formatUserDateTimeBucketRange,
  formatUserDateTimeShort,
  isOptionalFutureLocalDateTimeInput,
  localDateTimeInputFromDate,
  localDateTimeInputToUtcIso,
  minFutureLocalDateTimeInput,
  parseApiDateTime,
  userDateTimeFormatPattern,
  utcIsoToLocalDateTimeInput,
} from "../datetime";

describe("datetime", () => {
  beforeAll(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-04T12:00:00.000Z"));
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses API ISO timestamps", () => {
    const date = parseApiDateTime("2026-08-04T12:30:00.000Z");
    expect(date?.toISOString()).toBe("2026-08-04T12:30:00.000Z");
  });

  it("formats UTC timestamps in the browser local timezone", () => {
    vi.stubGlobal("Intl", {
      DateTimeFormat: () => ({
        resolvedOptions: () => ({ timeZone: "Europe/Moscow" }),
      }),
    });

    const formatted = formatUserDateTime("2026-08-04T12:30:00.000Z");
    expect(formatted).toMatch(/Aug 4, \d{2}:\d{2}$/);
    expect(formatted).not.toMatch(/AM|PM/i);
  });

  it("omits year for the current calendar year", () => {
    expect(formatUserDateTime("2026-03-15T10:00:00.000Z")).toBe(
      "Mar 15, 10:00",
    );
    expect(formatUserDateTimeShort("2026-03-15T10:00:00.000Z")).toBe(
      "Mar 15 10:00",
    );
    expect(
      userDateTimeFormatPattern(new Date("2026-03-15T10:00:00.000Z"), "date"),
    ).toBe("MMM d");
  });

  it("includes year when not the current calendar year", () => {
    expect(formatUserDateTime("2025-03-15T10:00:00.000Z")).toBe(
      "Mar 15, 2025, 10:00",
    );
    expect(formatUserDateTimeShort("2025-03-15T10:00:00.000Z")).toBe(
      "Mar 15, 2025 10:00",
    );
    expect(
      userDateTimeFormatPattern(new Date("2025-03-15T10:00:00.000Z"), "date"),
    ).toBe("MMM d, yyyy");
  });

  it("formats chart axis labels without AM/PM", () => {
    const hour = 60 * 60 * 1000;
    const day = 24 * hour;
    expect(formatUserDateTimeAxis("2026-08-04T12:00:00.000Z", hour)).toMatch(
      /Aug 4 \d{2}:\d{2}/,
    );
    expect(formatUserDateTimeAxis("2025-08-04T12:00:00.000Z", day)).toBe(
      "Aug 4, 2025",
    );
    expect(
      formatUserDateTimeAxis("2026-08-04T12:00:00.000Z", hour / 2),
    ).toMatch(/^\d{2}:\d{2}$/);
  });

  it("formats chart bucket tooltips in 24h format", () => {
    const hour = 60 * 60 * 1000;
    expect(
      formatUserDateTimeBucketRange("2026-08-04T10:00:00.000Z", hour),
    ).toBe("Aug 4, 10:00-11:00");
    expect(
      formatUserDateTimeBucketRange("2025-08-04T10:00:00.000Z", hour),
    ).toBe("Aug 4, 2025, 10:00-11:00");
  });

  it("converts datetime-local wall time to UTC ISO", () => {
    vi.useRealTimers();
    const originalDate = Date;
    class MockDate extends originalDate {
      constructor(value?: string | number | Date) {
        if (value === "2026-08-04T15:30") {
          super("2026-08-04T12:30:00.000Z");
          return;
        }
        super(value as string | number | Date);
      }
    }
    vi.stubGlobal("Date", MockDate as DateConstructor);

    expect(localDateTimeInputToUtcIso("2026-08-04T15:30")).toBe(
      "2026-08-04T12:30:00.000Z",
    );
    vi.unstubAllGlobals();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-04T12:00:00.000Z"));
  });

  it("converts UTC ISO to datetime-local input value", () => {
    vi.useRealTimers();
    const originalDate = Date;
    class MockDate extends originalDate {
      constructor(value?: string | number | Date) {
        super(value as string | number | Date);
      }

      getFullYear() {
        return 2026;
      }
      getMonth() {
        return 7;
      }
      getDate() {
        return 4;
      }
      getHours() {
        return 15;
      }
      getMinutes() {
        return 30;
      }
    }
    vi.stubGlobal("Date", MockDate as DateConstructor);

    expect(utcIsoToLocalDateTimeInput("2026-08-04T12:30:00.000Z")).toBe(
      "2026-08-04T15:30",
    );
    expect(
      localDateTimeInputFromDate(new MockDate("2026-08-04T12:30:00.000Z")),
    ).toBe("2026-08-04T15:30");
    vi.unstubAllGlobals();
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-04T12:00:00.000Z"));
  });

  it("computes minimum future datetime-local input from an offset", () => {
    const now = new Date("2026-08-04T12:00:00.000Z");
    const expected = localDateTimeInputFromDate(
      new Date(now.getTime() + 30 * 60 * 1000),
    );
    expect(minFutureLocalDateTimeInput(30 * 60 * 1000, now)).toBe(expected);
  });

  it("validates optional future datetime-local input", () => {
    const now = new Date("2026-08-04T12:00:00.000Z");
    const minDate = new Date(now.getTime() + 30 * 60 * 1000);
    const minLocal = localDateTimeInputFromDate(minDate);

    expect(isOptionalFutureLocalDateTimeInput("", minDate)).toBe(true);
    expect(isOptionalFutureLocalDateTimeInput(minLocal, minDate)).toBe(true);
    expect(
      isOptionalFutureLocalDateTimeInput(
        localDateTimeInputFromDate(new Date(now.getTime() + 29 * 60 * 1000)),
        minDate,
      ),
    ).toBe(false);
  });
});
