import { api, rawPost, rawPut } from "./client";
import { mapDiffResponse } from "./treeMappers";
import type {
  ChangeRequest,
  ChangeRequestComment,
  ChangeRequestListResponse,
  DiffResponse,
} from "./types";

export const changeRequestsApi = {
  list: (
    namespace: string,
    path: string,
    params?: { status?: string; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) =>
    api.get<ChangeRequestListResponse>(
      `/ns/${namespace}/~change-requests/${path}/~list/`,
      {
        params: params ?? {},
        signal,
      },
    ),

  get: (
    namespace: string,
    path: string,
    number: number,
    includeContent = false,
    signal?: AbortSignal,
  ) =>
    api.get<ChangeRequest>(`/ns/${namespace}/~change-requests/${path}`, {
      params: { number, include_content: includeContent },
      signal,
    }),

  create: (
    namespace: string,
    path: string,
    content: string,
    opts?: { title?: string; description?: string; base_version?: string },
  ) => {
    const qs = new URLSearchParams();
    if (opts?.title) qs.set("title", opts.title);
    if (opts?.description) qs.set("description", opts.description);
    if (opts?.base_version) qs.set("base_version", opts.base_version);
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return rawPost(
      `/ns/${namespace}/~change-requests/${path}${suffix}`,
      content,
    ) as Promise<ChangeRequest>;
  },

  update: (namespace: string, path: string, number: number, content: string) =>
    rawPut(
      `/ns/${namespace}/~change-requests/${path}?number=${number}`,
      content,
    ) as Promise<ChangeRequest>,

  patchMetadata: (
    namespace: string,
    path: string,
    number: number,
    payload: { title?: string; description?: string },
  ) =>
    api.patch<ChangeRequest>(
      `/ns/${namespace}/~change-requests/${path}`,
      payload,
      { params: { number } },
    ),

  approve: (namespace: string, path: string, number: number) =>
    api.post<ChangeRequest>(
      `/ns/${namespace}/~change-requests/${path}/~approve/`,
      {},
      { params: { number } },
    ),

  unapprove: (namespace: string, path: string, number: number) =>
    api.post<ChangeRequest>(
      `/ns/${namespace}/~change-requests/${path}/~unapprove/`,
      {},
      { params: { number } },
    ),

  reject: (namespace: string, path: string, number: number, reason = "") =>
    api.post<ChangeRequest>(
      `/ns/${namespace}/~change-requests/${path}/~reject/`,
      { reason },
      { params: { number } },
    ),

  withdraw: (namespace: string, path: string, number: number) =>
    api.post<ChangeRequest>(
      `/ns/${namespace}/~change-requests/${path}/~withdraw/`,
      {},
      { params: { number } },
    ),

  apply: (namespace: string, path: string, number: number) =>
    api.post<ChangeRequest>(
      `/ns/${namespace}/~change-requests/${path}/~apply/`,
      {},
      { params: { number } },
    ),

  diff: (
    namespace: string,
    path: string,
    number: number,
    against: "base" | "latest" = "base",
    reveal = false,
    signal?: AbortSignal,
  ) =>
    api
      .get<Parameters<typeof mapDiffResponse>[0]>(
        `/ns/${namespace}/~change-requests/${path}/~diff/`,
        { params: { number, against, reveal }, signal },
      )
      .then(mapDiffResponse) as Promise<DiffResponse>,

  listComments: (
    namespace: string,
    path: string,
    number: number,
    signal?: AbortSignal,
  ) =>
    api.get<{ items: ChangeRequestComment[]; total: number }>(
      `/ns/${namespace}/~change-requests/${path}/~comments/`,
      { params: { number }, signal },
    ),

  addComment: (
    namespace: string,
    path: string,
    number: number,
    body: string,
    anchor?: { start_line: number; end_line?: number },
  ) =>
    api.post<ChangeRequestComment>(
      `/ns/${namespace}/~change-requests/${path}/~comments/`,
      { body, anchor: anchor ?? null },
      { params: { number } },
    ),

  updateComment: (
    namespace: string,
    path: string,
    number: number,
    commentId: number,
    body: string,
  ) =>
    api.patch<ChangeRequestComment>(
      `/ns/${namespace}/~change-requests/${path}/~comments/${commentId}`,
      { body },
      { params: { number } },
    ),

  deleteComment: (
    namespace: string,
    path: string,
    number: number,
    commentId: number,
  ) =>
    api.delete<void>(
      `/ns/${namespace}/~change-requests/${path}/~comments/${commentId}`,
      { params: { number } },
    ),
};
