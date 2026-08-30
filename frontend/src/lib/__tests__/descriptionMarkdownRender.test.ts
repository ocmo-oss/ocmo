import { describe, expect, it } from "vitest";
import { isExternalMarkdownLink } from "../descriptionMarkdownRender";

describe("isExternalMarkdownLink", () => {
  const pageOrigin = "http://localhost:5173";

  it("treats off-site http links as external", () => {
    expect(isExternalMarkdownLink("https://example.com/docs", pageOrigin)).toBe(
      true,
    );
  });

  it("treats same-origin http links as internal", () => {
    expect(isExternalMarkdownLink(`${pageOrigin}/docs`, pageOrigin)).toBe(
      false,
    );
  });

  it("treats relative links as internal", () => {
    expect(isExternalMarkdownLink("/docs", pageOrigin)).toBe(false);
    expect(isExternalMarkdownLink("#section", pageOrigin)).toBe(false);
  });

  it("does not treat mailto links as external http links", () => {
    expect(isExternalMarkdownLink("mailto:hello@example.com", pageOrigin)).toBe(
      false,
    );
  });
});
