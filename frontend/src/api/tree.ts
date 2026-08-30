import { api, rawPost, rawPut } from "./client";
import { fetchConfigDataSchema } from "./schema";
import {
  mapDiffResponse,
  mapExtendedNode,
  mapNavigationResponse,
  mapNavigationNode,
  mapVersionHistoryResponse,
  unwrapPaginatedItems,
  mapResolveResponse,
  mapResolverCreateResponse,
} from "./treeMappers";
import type {
  DeleteResult,
  CopiedItems,
  ConfigNode,
  TagPayload,
  LocationPayload,
  DescribePayload,
  PropagationResult,
  ResolveParametersResponse,
  ResolverTokenRotationResponse,
} from "./types";

const base = (ns: string) => `/ns/${ns}`;

/** Tag POST endpoints need a trailing slash on the item path so the last segment is not parsed as a tag name. */
function tagItemBase(ns: string, path: string): string {
  const normalized = path.replace(/^\/+|\/+$/g, "");
  return `${base(ns)}/~tag/${normalized}/`;
}

export const treeApi = {
  navigate: (
    ns: string,
    path: string | null,
    params?: { recursive?: boolean; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) => {
    const endpoint = path
      ? `${base(ns)}/~navigate/${path}`
      : `${base(ns)}/~navigate/`;
    return api
      .get<Parameters<typeof mapNavigationResponse>[0]>(endpoint, {
        params,
        signal,
      })
      .then(mapNavigationResponse);
  },

  search: (
    ns: string,
    path: string | null,
    params?: { q?: string; types?: string; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) => {
    const endpoint = path
      ? `${base(ns)}/~search/${path}`
      : `${base(ns)}/~search/`;
    return api
      .get<
        | Parameters<typeof mapNavigationNode>[0][]
        | { items: Parameters<typeof mapNavigationNode>[0][] }
      >(endpoint, { params, signal })
      .then((raw) => unwrapPaginatedItems(raw).map(mapNavigationNode));
  },

  get: (
    ns: string,
    path: string,
    params?: { version?: string; reveal?: boolean },
    signal?: AbortSignal,
  ) =>
    api
      .get<Parameters<typeof mapExtendedNode>[0]>(`${base(ns)}/~get/${path}`, {
        params,
        signal,
      })
      .then(mapExtendedNode),

  versions: (
    ns: string,
    path: string,
    params?: { limit?: number; offset?: number; q?: string },
    signal?: AbortSignal,
  ) =>
    api
      .get<Parameters<typeof mapVersionHistoryResponse>[0]>(
        `${base(ns)}/~versions/${path}`,
        { params, signal },
      )
      .then(mapVersionHistoryResponse),

  diff: (
    ns: string,
    path: string,
    params?: { from?: string; to?: string; to_path?: string; reveal?: boolean },
    signal?: AbortSignal,
  ) =>
    api
      .get<Parameters<typeof mapDiffResponse>[0]>(`${base(ns)}/~diff/${path}`, {
        params,
        signal,
      })
      .then(mapDiffResponse),

  delete: (
    ns: string,
    path: string,
    params?: { preview?: boolean; version?: number },
    signal?: AbortSignal,
  ) =>
    api.delete<DeleteResult>(`${base(ns)}/~delete/${path}`, { params, signal }),

  move: (
    ns: string,
    path: string,
    payload: LocationPayload,
    options?: { skip_reference_validation?: boolean },
  ) =>
    api
      .post<Parameters<typeof mapExtendedNode>[0]>(
        `${base(ns)}/~move/${path}`,
        payload,
        {
          params: {
            ...(options?.skip_reference_validation
              ? { skip_reference_validation: true }
              : {}),
          },
        },
      )
      .then(mapExtendedNode),

  copy: (
    ns: string,
    path: string,
    payload: LocationPayload,
    options?: { tag_to_copy?: string; skip_reference_validation?: boolean },
  ) =>
    api.post<CopiedItems>(`${base(ns)}/~copy/${path}`, payload, {
      params: {
        ...(options?.tag_to_copy ? { tag_to_copy: options.tag_to_copy } : {}),
        ...(options?.skip_reference_validation
          ? { skip_reference_validation: true }
          : {}),
      },
    }),

  setTag: (ns: string, path: string, payload: TagPayload) =>
    api
      .post<Parameters<typeof mapExtendedNode>[0]>(
        tagItemBase(ns, path),
        payload,
      )
      .then((node) =>
        node ? (mapExtendedNode(node) as ConfigNode) : undefined,
      ),

  deleteTag: (ns: string, path: string, tag: string) =>
    api
      .post<Parameters<typeof mapExtendedNode>[0]>(tagItemBase(ns, path), {
        tag,
        version: null,
      })
      .then((node) =>
        node ? (mapExtendedNode(node) as ConfigNode) : undefined,
      ),

  describe: (ns: string, path: string, payload: DescribePayload) =>
    api
      .post<Parameters<typeof mapExtendedNode>[0]>(
        `${base(ns)}/~describe/${path}`,
        payload,
      )
      .then(mapExtendedNode),

  // Config
  createConfig: (ns: string, path: string, content: string) =>
    rawPost(`/ns/${ns}/~config/~create/${path}`, content),

  updateConfig: (ns: string, path: string, content: string) =>
    rawPut(`/ns/${ns}/~config/~update/${path}`, content).then(
      (raw) =>
        mapExtendedNode(
          raw as Parameters<typeof mapExtendedNode>[0],
        ) as ConfigNode,
    ),

  // Template
  createTemplate: (ns: string, path: string, content: string) =>
    rawPost(`/ns/${ns}/~template/~create/${path}`, content),

  updateTemplate: (ns: string, path: string, content: string) =>
    rawPut(`/ns/${ns}/~template/~update/${path}`, content),

  // Secret
  createSecret: (ns: string, path: string, content: string) =>
    rawPost(`/ns/${ns}/~secret/~create/${path}`, content),

  updateSecret: (ns: string, path: string, content: string) =>
    rawPut(`/ns/${ns}/~secret/~update/${path}`, content),

  // Resolver
  createResolver: (ns: string, path: string, content: string) =>
    rawPost(`/ns/${ns}/~resolver/~create/${path}`, content).then((raw) =>
      mapResolverCreateResponse(
        raw as { path: string; token1?: string | null },
      ),
    ),

  updateResolver: (ns: string, path: string, content: string) =>
    rawPut(`/ns/${ns}/~resolver/~update/${path}`, content),

  rotateToken: (ns: string, path: string, payload: { token_number: 1 | 2 }) =>
    api.post<ResolverTokenRotationResponse>(
      `${base(ns)}/~resolver/~rotate-token/${path}`,
      payload,
    ),

  // Resolve
  resolve: (
    ns: string,
    path: string,
    params?: Record<string, string | number | boolean | undefined | null>,
    signal?: AbortSignal,
  ) =>
    api
      .get<Parameters<typeof mapResolveResponse>[0]>(
        `${base(ns)}/~resolve/${path}`,
        { params, signal },
      )
      .then(mapResolveResponse),

  resolveParameters: (
    ns: string,
    path: string,
    params?: Record<string, string | boolean | undefined | null>,
    signal?: AbortSignal,
  ) =>
    api.get<ResolveParametersResponse>(
      `${base(ns)}/~resolve-parameters/${path}`,
      { params, signal },
    ),

  resolveDraft: (
    ns: string,
    path: string,
    content: string,
    params?: Record<string, string | boolean | undefined | null>,
  ) => {
    const qs = new URLSearchParams();
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null) qs.set(k, String(v));
      }
    }
    const query = qs.toString();
    return rawPost(
      `/ns/${ns}/~resolve-draft/${path}${query ? `?${query}` : ""}`,
      content,
    ).then((raw) =>
      mapResolveResponse(raw as Parameters<typeof mapResolveResponse>[0]),
    );
  },

  // Propagation
  propagate: (ns: string, path: string, version?: string) =>
    api.post<PropagationResult>(`${base(ns)}/~propagate/${path}`, undefined, {
      params: version ? { version } : undefined,
    }),

  configSchema: (
    ns: string,
    path: string,
    params?: { version?: string },
    signal?: AbortSignal,
  ) => fetchConfigDataSchema(ns, path, params, signal),
};
