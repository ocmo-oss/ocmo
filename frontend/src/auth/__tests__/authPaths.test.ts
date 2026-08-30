import { describe, expect, it } from "vitest";
import {
  isOidcCallbackPath,
  LOGIN_CALLBACK_PATH,
  LOGIN_PATH,
  SILENT_CALLBACK_PATH,
  shouldSkipSilentRenew,
} from "../authPaths";

describe("authPaths", () => {
  it("recognises interactive and silent OIDC callback paths", () => {
    expect(LOGIN_CALLBACK_PATH).toBe("/login/callback");
    expect(SILENT_CALLBACK_PATH).toBe("/auth/silent-callback");
    expect(isOidcCallbackPath("/login/callback")).toBe(true);
    expect(isOidcCallbackPath("/auth/silent-callback")).toBe(true);
    expect(isOidcCallbackPath("/ns/demo/configs")).toBe(false);
  });

  it("skips silent renew on login and callback paths", () => {
    expect(shouldSkipSilentRenew(LOGIN_PATH)).toBe(true);
    expect(shouldSkipSilentRenew("/login/callback")).toBe(true);
    expect(shouldSkipSilentRenew("/auth/silent-callback")).toBe(true);
    expect(shouldSkipSilentRenew("/ns/demo/configs")).toBe(false);
  });
});
