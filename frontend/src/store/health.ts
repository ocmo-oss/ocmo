import { create } from "zustand";
import type {
  BuiltinNamespacePaths,
  HealthResponse,
  ReservedTags,
} from "../api/types";
import {
  DEFAULT_BUILTIN_NAMESPACE_PATHS,
  DEFAULT_CONFIG_METADATA_KEY,
  DEFAULT_RESERVED_TAGS,
  pickVersionBootstrap,
} from "./versionBootstrap";
import type { VersionResponse } from "../api/types";

export { DEFAULT_CONFIG_METADATA_KEY } from "./versionBootstrap";

interface HealthState {
  health: HealthResponse | null;
  healthError: string | null;
  version: string | null;
  configMetadataKey: string | null;
  builtinNamespacePaths: BuiltinNamespacePaths;
  reservedTags: ReservedTags;
  setHealth: (h: HealthResponse) => void;
  setHealthError: (message: string) => void;
  clearAvailabilityError: () => void;
  applyVersionResponse: (version: VersionResponse) => void;
  setVersionBootstrapFallback: () => void;
}

export const useHealthStore = create<HealthState>((set) => ({
  health: null,
  healthError: null,
  version: null,
  configMetadataKey: null,
  builtinNamespacePaths: DEFAULT_BUILTIN_NAMESPACE_PATHS,
  reservedTags: DEFAULT_RESERVED_TAGS,
  setHealth: (h) => set({ health: h, healthError: null }),
  setHealthError: (message) => set({ healthError: message, health: null }),
  clearAvailabilityError: () =>
    set((state) => (state.healthError ? { healthError: null } : state)),
  applyVersionResponse: (version) => set(pickVersionBootstrap(version)),
  setVersionBootstrapFallback: () =>
    set({
      version: "unknown",
      configMetadataKey: DEFAULT_CONFIG_METADATA_KEY,
      builtinNamespacePaths: DEFAULT_BUILTIN_NAMESPACE_PATHS,
      reservedTags: DEFAULT_RESERVED_TAGS,
    }),
}));

export function useConfigMetadataKey(): string {
  return (
    useHealthStore((state) => state.configMetadataKey) ??
    DEFAULT_CONFIG_METADATA_KEY
  );
}

export function useBuiltinNamespacePaths(): BuiltinNamespacePaths {
  return useHealthStore((state) => state.builtinNamespacePaths);
}

export function useReservedTags(): ReservedTags {
  return useHealthStore((state) => state.reservedTags);
}

export function isHealthy(): boolean {
  const { health, healthError } = useHealthStore.getState();
  if (healthError) return false;
  if (health === null) return true;
  return health.status === "ok";
}

export function formatHealthDetail(
  health: HealthResponse | null,
  healthError: string | null,
): string {
  if (healthError) return healthError;
  if (!health) return "Checking API health…";
  if (health.status === "ok") {
    const checks = Object.keys(health.checks);
    return checks.length > 0
      ? `All checks passed (${checks.join(", ")})`
      : "All health checks passed";
  }

  const failed = Object.entries(health.checks)
    .filter(([, check]) => check.status !== "ok")
    .map(([name, check]) => `${name}: ${check.message ?? check.status}`);

  return failed.length > 0 ? failed.join("\n") : `API status: ${health.status}`;
}
