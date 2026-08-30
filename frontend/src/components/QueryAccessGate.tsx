import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import { ApiUnavailable } from "./ApiUnavailable";
import { isApiUnavailableError } from "../lib/apiAvailability";
import { PermissionDenied } from "./items/PermissionDenied";

function queryErrorStatus(error: unknown): number | undefined {
  if (error instanceof ApiError) return error.status;
  const status = (error as Error & { status?: number }).status;
  return typeof status === "number" ? status : undefined;
}

interface QueryAccessGateProps {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  hasData: boolean;
  loadingFallback: ReactNode;
  permissionDeniedMessage?: string;
  notFoundMessage?: string;
  emptyFallback?: ReactNode;
  children: ReactNode;
}

export function QueryAccessGate({
  isLoading,
  isError,
  error,
  hasData,
  loadingFallback,
  permissionDeniedMessage = "You do not have permission to view this page.",
  notFoundMessage = "Not found.",
  emptyFallback,
  children,
}: QueryAccessGateProps) {
  if (isLoading && !hasData) {
    return <>{loadingFallback}</>;
  }

  if (isError) {
    const status = queryErrorStatus(error);
    if (status === 403) {
      return <PermissionDenied message={permissionDeniedMessage} />;
    }
    if (status === 404) {
      return (
        <div className="flex h-full items-center justify-center p-6">
          <p className="text-sm text-gray-500">{notFoundMessage}</p>
        </div>
      );
    }
    if (isApiUnavailableError(error)) {
      const detail = error instanceof ApiError ? error.detail : undefined;
      return <ApiUnavailable message={detail} />;
    }
    const msg = error instanceof Error ? error.message : "Failed to load.";
    return (
      <div className="flex h-full items-center justify-center p-6">
        <p className="text-sm text-red-500">{msg}</p>
      </div>
    );
  }

  if (!hasData && emptyFallback) {
    return <>{emptyFallback}</>;
  }

  return <>{children}</>;
}

export function isPermissionDeniedError(error: unknown): boolean {
  return queryErrorStatus(error) === 403;
}

export function isApiUnavailableQueryError(error: unknown): boolean {
  return isApiUnavailableError(error);
}
