import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  cspDevelopment,
  cspProduction,
  cspProductionRequirements,
} from "../../../csp";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "../../..");

function directiveValue(csp: string, name: string): string | undefined {
  return csp
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name} `))
    ?.slice(name.length + 1);
}

function expectDirective(csp: string, name: string): string {
  const value = directiveValue(csp, name);
  expect(value, `missing ${name} directive`).toBeDefined();
  return value!;
}

describe("CSP policy", () => {
  it("production disallows inline and eval scripts", () => {
    const scriptSrc = expectDirective(cspProduction, "script-src");
    expect(scriptSrc).toBe("'self'");
    expect(cspProduction).not.toMatch(/unsafe-eval/);
    expect(cspProduction).not.toMatch(/script-src[^;]*unsafe-inline/);
  });

  it("development allows inline scripts only for Vite HMR", () => {
    const scriptSrc = expectDirective(cspDevelopment, "script-src");
    expect(scriptSrc).toContain("'unsafe-inline'");
    expect(cspDevelopment).not.toMatch(/unsafe-eval/);
  });

  it("allows same-origin framing for OIDC silent renew but blocks plugins", () => {
    for (const csp of [cspProduction, cspDevelopment]) {
      expect(expectDirective(csp, "frame-ancestors")).toBe("'self'");
      expect(expectDirective(csp, "object-src")).toBe("'none'");
    }
  });

  it("development connect-src allows local HTTP API and IdP", () => {
    const connectSrc = expectDirective(cspDevelopment, "connect-src");
    expect(connectSrc).toContain("http:");
  });

  it("nginx header snippet matches production policy", () => {
    const nginxHeaders = readFileSync(
      join(frontendRoot, "nginx-security-headers.inc"),
      "utf8",
    );
    expect(nginxHeaders).toContain(cspProduction);
  });

  it("production CSP satisfies documented app requirements", () => {
    for (const req of cspProductionRequirements) {
      const value = expectDirective(cspProduction, req.directive);
      for (const token of req.tokens) {
        expect(
          value.split(/\s+/),
          `${req.feature} (${req.directive})`,
        ).toContain(token);
      }
    }
  });
});
