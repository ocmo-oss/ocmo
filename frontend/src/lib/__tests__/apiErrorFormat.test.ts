import { describe, expect, it } from "vitest";
import { formatServerErrorDetail, parseApiErrorBody } from "../apiErrorFormat";

describe("formatServerErrorDetail", () => {
  it("joins validation error lists with newlines", () => {
    expect(
      formatServerErrorDetail({
        error: [
          "name: Field required",
          "description: String should have at most 4096 characters",
        ],
        errors: [
          "name: Field required",
          "description: String should have at most 4096 characters",
        ],
      }),
    ).toBe(
      "name: Field required\ndescription: String should have at most 4096 characters",
    );
  });

  it("prefers errors over error when both are present", () => {
    expect(
      formatServerErrorDetail({
        error: "legacy",
        errors: ["name: Field required"],
      }),
    ).toBe("name: Field required");
  });

  it("falls back to detail for older payloads", () => {
    expect(formatServerErrorDetail({ detail: "Not found" })).toBe("Not found");
  });
});

describe("parseApiErrorBody", () => {
  it("parses JSON validation payloads", () => {
    const detail = parseApiErrorBody(
      422,
      JSON.stringify({
        error: ["name: Field required"],
        errors: ["name: Field required"],
      }),
    );
    expect(detail).toBe("name: Field required");
  });
});
