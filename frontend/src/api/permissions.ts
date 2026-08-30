import { api } from "./client";
import type {
  GlobalPermissionRule,
  GlobalPermissionRulesList,
  GlobalPermissionRulePayload,
  GlobalPermissionMovePaylod,
} from "./types";

export const permissionsApi = {
  list: (params?: { limit?: number; offset?: number }, signal?: AbortSignal) =>
    api.get<GlobalPermissionRulesList>("/global-permissions/", {
      params,
      signal,
    }),

  get: (ruleId: string, signal?: AbortSignal) =>
    api.get<GlobalPermissionRule>(`/global-permissions/${ruleId}`, { signal }),

  create: (payload: GlobalPermissionRulePayload) =>
    api.post<GlobalPermissionRule>("/global-permissions/", payload),

  update: (ruleId: string, payload: GlobalPermissionRulePayload) =>
    api.put<GlobalPermissionRule>(`/global-permissions/${ruleId}`, payload),

  delete: (ruleId: string) => api.delete<void>(`/global-permissions/${ruleId}`),

  move: (ruleId: string, payload: GlobalPermissionMovePaylod) =>
    api.post<GlobalPermissionRule>(
      `/global-permissions/${ruleId}/~move/`,
      payload,
    ),
};
