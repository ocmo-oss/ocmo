import type {
  AnyExtendedNode,
  ConfigNode,
  DiffResponse,
  FolderNode,
  ItemType,
  NavigationResponse,
  ResolverNode,
  ResolverCreateResponse,
  ResolveParticipant,
  ResolveResponse,
  SecretNode,
  TagInfo,
  TreeNavigationNode,
  VersionHistoryResponse,
} from "./types";

type RawNavNode = {
  name: string;
  path: string;
  node_type: ItemType;
};

type RawVersionData = {
  version: string | number;
  tags?: string[];
  data?: string | null;
  updater?: string;
  updated_at?: string;
  deleted_at?: string | null;
};

type RawBaseNode = {
  name: string;
  path: string;
  node_type: ItemType;
  description?: string;
  author?: string;
  created_at?: string;
  updated_at?: string;
  tags?: Record<string, number>;
  version_data?: RawVersionData;
  configuration?: string | null;
  token1?: string | null;
  token1_last_used?: string | null;
  token2?: string | null;
  token2_last_used?: string | null;
  children_count?: number;
};

type RawNavigationResponse = {
  item: RawNavNode | null;
  children: RawNavNode[];
  children_count: number;
  breadcrumbs: string[];
  is_leaf: boolean;
};

type RawVersionHistoryResponse = {
  item: RawBaseNode;
  versions: Array<{
    version: number;
    tags: string[];
    updater: string;
    updated_at: string;
    deleted_at: string | null;
  }>;
  versions_count: number;
};

type RawDiffSide = {
  path: string;
  version: number;
  data?: string | null;
};

type RawDiffResponse = {
  from_side: RawDiffSide;
  to_side: RawDiffSide;
  decryption_required?: boolean;
};

function tagsFromRecord(tags?: Record<string, number>): TagInfo[] {
  if (!tags) return [];
  return Object.entries(tags).map(([name, version]) => ({ name, version }));
}

export function mapNavigationNode(raw: RawNavNode): TreeNavigationNode {
  return {
    name: raw.name,
    path: raw.path,
    type: raw.node_type,
    is_leaf: raw.node_type !== "folder",
  };
}

export function mapNavigationResponse(
  raw: RawNavigationResponse,
): NavigationResponse {
  return {
    item: raw.item ? mapNavigationNode(raw.item) : null,
    children: raw.children.map(mapNavigationNode),
    breadcrumbs: raw.breadcrumbs.map((path) => ({
      path,
      name: path.split("/").pop() ?? path,
    })),
    is_leaf: raw.is_leaf,
    count: raw.children_count,
  };
}

function mapVersionedNode(
  raw: RawBaseNode,
  type: "config" | "template",
): ConfigNode;
function mapVersionedNode(raw: RawBaseNode, type: "secret"): SecretNode;
function mapVersionedNode(
  raw: RawBaseNode,
  type: "config" | "template" | "secret",
): ConfigNode | SecretNode {
  const versionData = raw.version_data;
  const version = versionData ? Number(versionData.version) : 0;
  const updatedAt = versionData?.updated_at ?? new Date(0).toISOString();

  const base = {
    path: raw.path,
    name: raw.name,
    description: raw.description,
    version,
    tags: tagsFromRecord(raw.tags),
    updater: versionData?.updater ?? "",
    created_at: updatedAt,
    updated_at: updatedAt,
    deleted_at: versionData?.deleted_at ?? null,
  };

  if (type === "secret") {
    return {
      ...base,
      type: "secret",
      content: versionData?.data ?? undefined,
    };
  }

  return {
    ...base,
    type,
    content: versionData?.data ?? "",
  };
}

export function mapExtendedNode(raw: RawBaseNode): AnyExtendedNode {
  switch (raw.node_type) {
    case "config":
    case "template":
      return mapVersionedNode(raw, raw.node_type);
    case "secret":
      return mapVersionedNode(raw, "secret");
    case "resolver": {
      const createdAt =
        raw.created_at ??
        raw.version_data?.updated_at ??
        new Date(0).toISOString();
      const updatedAt = raw.updated_at ?? createdAt;
      return {
        path: raw.path,
        name: raw.name,
        type: "resolver",
        description: raw.description,
        version: 1,
        author: raw.author ?? "",
        token1: raw.token1 ?? "",
        token1_last_used: raw.token1_last_used ?? null,
        token2: raw.token2 ?? null,
        token2_last_used: raw.token2_last_used ?? null,
        configuration: raw.configuration ?? undefined,
        created_at: createdAt,
        updated_at: updatedAt,
      } satisfies ResolverNode;
    }
    case "folder":
      return {
        path: raw.path,
        name: raw.name,
        type: "folder",
        description: raw.description,
        children_count: raw.children_count ?? 0,
      } satisfies FolderNode;
    default:
      throw new Error(`Unknown node type: ${String(raw.node_type)}`);
  }
}

export function mapResolverCreateResponse(raw: {
  path: string;
  token1?: string | null;
}): ResolverCreateResponse {
  return {
    path: raw.path,
    token1: raw.token1 ?? "",
  };
}

export function mapVersionHistoryResponse(
  raw: RawVersionHistoryResponse,
): VersionHistoryResponse {
  return {
    path: raw.item.path,
    type: raw.item.node_type,
    tags: tagsFromRecord(raw.item.tags),
    versions: raw.versions.map((version) => ({
      version: version.version,
      tags: version.tags ?? [],
      updater: version.updater,
      created_at: version.updated_at,
      deleted_at: version.deleted_at,
      size: null,
    })),
    count: raw.versions_count,
  };
}

export function mapDiffResponse(raw: RawDiffResponse): DiffResponse {
  return {
    from: {
      path: raw.from_side.path,
      version: raw.from_side.version,
      content: raw.from_side.data ?? null,
      decryption_required: raw.decryption_required,
    },
    to: {
      path: raw.to_side.path,
      version: raw.to_side.version,
      content: raw.to_side.data ?? null,
      decryption_required: raw.decryption_required,
    },
  };
}

export function unwrapPaginatedItems<T>(raw: T[] | { items: T[] }): T[] {
  return Array.isArray(raw) ? raw : raw.items;
}

type RawResolvedItem = {
  name: string;
  version: number;
  format: string;
  url?: string | null;
  checksum?: string | null;
  trace?: Record<string, unknown>;
};

type RawResolveResponse = {
  items?: RawResolvedItem[];
  length?: number;
  trace_only?: boolean;
  root?: unknown;
};

function mapResolveTrace(
  trace?: Record<string, unknown>,
): Record<string, ResolveParticipant> | undefined {
  if (!trace || Object.keys(trace).length === 0) return undefined;

  const mapped: Record<string, ResolveParticipant> = {};
  for (const [key, value] of Object.entries(trace)) {
    const meta = (value ?? {}) as Record<string, unknown>;
    const at = key.lastIndexOf("@");
    const path = at >= 0 ? key.slice(0, at) : key;
    const versionFromKey = at >= 0 ? Number(key.slice(at + 1)) : 0;

    mapped[key] = {
      resource_type:
        (meta.resource_type as ResolveParticipant["resource_type"]) ?? "config",
      path: typeof meta.path === "string" ? meta.path : path,
      version: typeof meta.version === "number" ? meta.version : versionFromKey,
      resolve_role:
        (meta.resolve_role as ResolveParticipant["resolve_role"]) ??
        "transitive",
      from_cache: Boolean(meta.from_cache),
    };
  }
  return mapped;
}

export function mapResolveResponse(raw: RawResolveResponse): ResolveResponse {
  const items = raw.items ?? [];
  const artifacts = items.map((item) => ({
    name: item.name,
    path: item.name,
    url: item.url ?? "",
    version: item.version,
    cast: item.format,
    from_cache: "miss" as const,
  }));

  const trace: Record<string, ResolveParticipant> = {};
  for (const item of items) {
    const itemTrace = mapResolveTrace(item.trace);
    if (itemTrace) Object.assign(trace, itemTrace);
  }

  return {
    artifacts,
    trace: Object.keys(trace).length > 0 ? trace : undefined,
    trace_only: raw.trace_only,
  };
}
