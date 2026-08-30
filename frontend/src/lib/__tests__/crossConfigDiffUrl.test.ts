import { describe, expect, it } from "vitest";
import {
  buildCrossConfigDiffSearchParams,
  crossConfigDiffSearchParamsEqual,
  parseCrossConfigDiffSearchParams,
} from "../crossConfigDiffUrl";

describe("crossConfigDiffUrl", () => {
  it("parses diff deep-link query params", () => {
    const params = new URLSearchParams(
      "from=app%2Fa.conf&to=app%2Fb.conf&from_ref=v2&to_ref=stable&reveal=1",
    );

    expect(parseCrossConfigDiffSearchParams(params)).toEqual({
      fromPath: "app/a.conf",
      toPath: "app/b.conf",
      fromRef: "v2",
      toRef: "stable",
      reveal: true,
    });
  });

  it("builds diff deep-link query params with defaults omitted", () => {
    const params = buildCrossConfigDiffSearchParams({
      fromPath: "app/a.conf",
      toPath: "app/b.conf",
      fromRef: "latest",
      toRef: "latest",
      reveal: false,
    });

    expect(params.toString()).toBe("from=app%2Fa.conf&to=app%2Fb.conf");
  });

  it("builds diff deep-link query params with refs and reveal", () => {
    const params = buildCrossConfigDiffSearchParams({
      fromPath: "secret",
      toPath: "other/secret",
      fromRef: "v1",
      toRef: "v3",
      reveal: true,
    });

    expect(params.get("from")).toBe("secret");
    expect(params.get("to")).toBe("other/secret");
    expect(params.get("from_ref")).toBe("v1");
    expect(params.get("to_ref")).toBe("v3");
    expect(params.get("reveal")).toBe("1");
  });

  it("compares search param strings", () => {
    const left = buildCrossConfigDiffSearchParams({
      fromPath: "a",
      toPath: "b",
      fromRef: "latest",
      toRef: "latest",
      reveal: false,
    });
    const right = new URLSearchParams("from=a&to=b");

    expect(crossConfigDiffSearchParamsEqual(left, right)).toBe(true);
  });
});
