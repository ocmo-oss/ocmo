import { api } from './client'
import type {
  Namespace,
  NamespaceCreate,
  NamespacePatch,
  PaginatedResponse,
} from './types'

export const namespacesApi = {
  list: (params?: { name_filter?: string; limit?: number; offset?: number }, signal?: AbortSignal) =>
    api.get<PaginatedResponse<Namespace>>('/ns/', { params, signal }),

  get: (ns: string, signal?: AbortSignal) =>
    api.get<Namespace>(`/ns/${ns}`, { signal }),

  create: (payload: NamespaceCreate) =>
    api.post<Namespace>('/ns/', payload),

  update: (ns: string, payload: NamespacePatch) =>
    api.patch<Namespace>(`/ns/${ns}`, payload),

  delete: (ns: string) =>
    api.delete<void>(`/ns/${ns}`),
}
