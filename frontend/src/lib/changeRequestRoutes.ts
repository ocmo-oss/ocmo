import type { ChangeRequestReferrer } from "../api/types";

export function changeRequestRefLabel(path: string, number: number): string {
  return `${path}@~${number}`;
}

export function changeRequestDetailHref(
  namespace: string,
  referrer: Pick<ChangeRequestReferrer, "path" | "node_type" | "number">,
): string {
  const collection =
    referrer.node_type === "template"
      ? "templates"
      : referrer.node_type === "secret"
        ? "secrets"
        : "configs";
  return `/ns/${namespace}/${collection}/${referrer.path}/change-requests/${referrer.number}`;
}

/** True when the configs area is showing a change-request detail view. */
export function isChangeRequestDetailRoute(pathname: string): boolean {
  return /\/configs\/.+\/change-requests\/\d+\/?$/.test(pathname);
}

export function parseChangeRequestRoute(pathname: string): {
  namespace: string;
  itemPath: string;
  number: number;
} | null {
  const m = pathname.match(
    /^\/ns\/([^/]+)\/configs\/(.+)\/change-requests\/(\d+)\/?$/,
  );
  if (!m) return null;
  return { namespace: m[1], itemPath: m[2], number: Number(m[3]) };
}
