import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import {
  formatApiErrorDetail,
  formatFetchFailureMessage,
  isApiUnavailableError,
  isApiUnavailableStatus,
} from "../apiAvailability";

describe("isApiUnavailableStatus", () => {
  it("detects gateway failures", () => {
    expect(isApiUnavailableStatus(502)).toBe(true);
    expect(isApiUnavailableStatus(503)).toBe(true);
    expect(isApiUnavailableStatus(504)).toBe(true);
  });

  it("ignores other statuses", () => {
    expect(isApiUnavailableStatus(500)).toBe(false);
    expect(isApiUnavailableStatus(404)).toBe(false);
  });
});

describe("isApiUnavailableError", () => {
  it("detects ApiError gateway failures", () => {
    const error = new ApiError(502, "<html>", formatApiErrorDetail(502));
    expect(isApiUnavailableError(error)).toBe(true);
  });

  it("ignores other errors", () => {
    expect(isApiUnavailableError(new ApiError(500, "", "boom"))).toBe(false);
    expect(isApiUnavailableError(new Error("boom"))).toBe(false);
  });
});

describe("formatApiErrorDetail", () => {
  it("returns a user-facing message for 502", () => {
    expect(formatApiErrorDetail(502)).toContain("temporarily unavailable");
  });
});

describe("formatFetchFailureMessage", () => {
  it("uses ApiError detail", () => {
    const error = new ApiError(502, "", formatApiErrorDetail(502));
    expect(formatFetchFailureMessage(error)).toBe(error.detail);
  });

  it("maps network failures to a friendly message", () => {
    expect(
      formatFetchFailureMessage(new TypeError("Failed to fetch")),
    ).toContain("Unable to reach the API");
  });
});
