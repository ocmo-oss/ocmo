import { describe, expect, it } from "vitest";
import {
  parseDeletePreviewLine,
  parseDeletePreviewLines,
} from "../deletePreview";

describe("parseDeletePreviewLine", () => {
  it("parses tree item entries", () => {
    expect(
      parseDeletePreviewLine(
        "my-first-namespace:: Folder:: test/empty/soempty",
      ),
    ).toEqual({
      type: "folder",
      path: "test/empty/soempty",
    });
    expect(parseDeletePreviewLine("prod:: Config:: app/api")).toEqual({
      type: "config",
      path: "app/api",
    });
    expect(parseDeletePreviewLine("prod:: Folder:: app")).toEqual({
      type: "folder",
      path: "app",
    });
    expect(parseDeletePreviewLine("prod:: Secret:: creds/db")).toEqual({
      type: "secret",
      path: "creds/db",
    });
    expect(parseDeletePreviewLine("prod:: Resolver:: hooks/main")).toEqual({
      type: "resolver",
      path: "hooks/main",
    });
    expect(parseDeletePreviewLine("prod:: Template:: mail/welcome")).toEqual({
      type: "template",
      path: "mail/welcome",
    });
  });

  it("preserves version suffix in path", () => {
    expect(parseDeletePreviewLine("prod:: Config:: app/api@3")).toEqual({
      type: "config",
      path: "app/api@3",
    });
  });

  it("falls back for unknown formats", () => {
    expect(parseDeletePreviewLine("app/api")).toEqual({
      type: "config",
      path: "app/api",
    });
  });
});

describe("parseDeletePreviewLines", () => {
  it("parses multiple lines", () => {
    expect(
      parseDeletePreviewLines([
        "prod:: Folder:: app",
        "prod:: Config:: app/api",
      ]),
    ).toEqual([
      { type: "folder", path: "app" },
      { type: "config", path: "app/api" },
    ]);
  });
});
