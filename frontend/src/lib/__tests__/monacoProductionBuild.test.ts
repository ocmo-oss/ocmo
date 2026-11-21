import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), "../../..");
const distAssets = join(frontendRoot, "dist/assets");

function findEntryBundles(): string[] {
  if (!existsSync(distAssets)) return [];
  return readdirSync(distAssets).filter(
    (name) => name.startsWith("index-") && name.endsWith(".js"),
  );
}

function findEditorWorkerChunks(): string[] {
  if (!existsSync(distAssets)) return [];
  return readdirSync(distAssets).filter(
    (name) => name.startsWith("editorWebWorkerMain-") && name.endsWith(".js"),
  );
}

const hasProductionBuild = findEntryBundles().length > 0;

describe.skipIf(!hasProductionBuild)(
  "production build — Monaco worker CSP",
  () => {
    it("emits a same-origin editor worker chunk", () => {
      const workerChunks = findEditorWorkerChunks();
      expect(workerChunks.length).toBeGreaterThanOrEqual(1);
      for (const name of workerChunks) {
        const body = readFileSync(join(distAssets, name), "utf8");
        expect(body.length).toBeGreaterThan(10_000);
      }
    });

    it("wires MonacoEnvironment.getWorker in the entry bundle (not data: worker URLs)", () => {
      for (const name of findEntryBundles()) {
        const body = readFileSync(join(distAssets, name), "utf8");
        expect(body).toMatch(/MonacoEnvironment=\{[^}]*getWorker/);
        expect(body).not.toMatch(
          /MonacoEnvironment=\{[^}]*getWorkerUrl[^}]*data:text\/javascript/,
        );
        const envIdx = body.indexOf("MonacoEnvironment");
        if (envIdx >= 0) {
          const window = body.slice(envIdx, envIdx + 400);
          expect(window).not.toContain("data:text/javascript");
        }
      }
    });
  },
);
