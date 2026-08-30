import { describe, expect, it } from "vitest";
import {
  applyCastOptionChange,
  getCastOptionFieldState,
} from "../castOptionConstraints";
import type { JsonSchemaProperty } from "../castOptionsSchema";

const envProperties: Record<string, JsonSchemaProperty> = {
  type: { default: "unix", enum: ["unix", "windows", "powershell"] },
  export: { default: true, "x-ocmo-enabled-when": { type: "unix" } },
  uppercase: { default: false, "x-ocmo-incompatible-with": ["lowercase"] },
  lowercase: { default: false, "x-ocmo-incompatible-with": ["uppercase"] },
  list_format: {
    default: "indexed",
    enum: ["indexed", "joined", "json", "space"],
  },
  list_separator: {
    default: ",",
    "x-ocmo-enabled-when": { list_format: "joined" },
  },
};

describe("castOptionConstraints", () => {
  it("disables lowercase when uppercase is enabled", () => {
    const state = getCastOptionFieldState(
      "lowercase",
      envProperties.lowercase!,
      envProperties,
      { uppercase: true },
    );
    expect(state.disabled).toBe(true);
  });

  it("disables export for non-unix dialect", () => {
    const state = getCastOptionFieldState(
      "export",
      envProperties.export!,
      envProperties,
      { type: "powershell" },
    );
    expect(state.disabled).toBe(true);
  });

  it("clears incompatible fields when enabling uppercase", () => {
    const next = applyCastOptionChange("uppercase", true, envProperties, {
      lowercase: true,
    });
    expect(next.uppercase).toBe(true);
    expect(next.lowercase).toBeUndefined();
  });
});
