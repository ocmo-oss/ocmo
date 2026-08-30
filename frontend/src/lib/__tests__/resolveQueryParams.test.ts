import { describe, expect, it } from "vitest";
import { buildResolveQueryParams } from "../resolveQueryParams";

describe("buildResolveQueryParams", () => {
  it("omits no-creds when credentials are requested", () => {
    expect(
      buildResolveQueryParams({
        noCreds: false,
        dynamicParams: {},
      }),
    ).toEqual({ version: "latest" });
  });

  it("includes no-creds only when credentials should be skipped", () => {
    expect(
      buildResolveQueryParams({
        noCreds: true,
        dynamicParams: {},
      }),
    ).toEqual({ version: "latest", "no-creds": true });
  });

  it("passes dynamic parameters and cast options", () => {
    expect(
      buildResolveQueryParams({
        versionRef: "v3",
        noCreds: false,
        dynamicParams: { env: "prod" },
        cast: "json",
        markStable: true,
        castOptions: { indent: "2" },
      }),
    ).toEqual({
      version: "v3",
      "mark-stable": true,
      cast: "json",
      param_env: "prod",
      cast_option_indent: "2",
    });
  });

  it("passes ignore-configs-with-missing-tags for folder resolve", () => {
    expect(
      buildResolveQueryParams({
        noCreds: false,
        dynamicParams: {},
        ignoreConfigsWithMissingTags: true,
      }),
    ).toEqual({
      version: "latest",
      "ignore-configs-with-missing-tags": true,
    });
  });
});
