import { describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { formatApiErrorDetail } from "../../lib/apiAvailability";
import {
  isApiUnavailableQueryError,
  isPermissionDeniedError,
} from "../QueryAccessGate";

describe("isPermissionDeniedError", () => {
  it("detects ApiError 403", () => {
    expect(isPermissionDeniedError(new ApiError(403, "", "nope"))).toBe(true);
  });

  it("returns false for other errors", () => {
    expect(isPermissionDeniedError(new ApiError(404, "", "missing"))).toBe(
      false,
    );
    expect(isPermissionDeniedError(new Error("boom"))).toBe(false);
  });
});

describe("isApiUnavailableQueryError", () => {
  it("detects ApiError 502", () => {
    expect(
      isApiUnavailableQueryError(
        new ApiError(502, "<html>", formatApiErrorDetail(502)),
      ),
    ).toBe(true);
  });

  it("returns false for other errors", () => {
    expect(isApiUnavailableQueryError(new ApiError(500, "", "boom"))).toBe(
      false,
    );
  });
});
