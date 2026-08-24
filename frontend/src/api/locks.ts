import { api } from './client'
import { localDateTimeInputToUtcIso } from '../lib/datetime'
import type { Lock, LocksList, LockPayload } from './types'

export const locksApi = {
  list: (ns: string, params?: { limit?: number; offset?: number }, signal?: AbortSignal) =>
    api.get<LocksList>(`/ns/${ns}/~lock/`, { params, signal }),

  get: (ns: string, path: string, signal?: AbortSignal) =>
    api.get<Lock>(`/ns/${ns}/~lock/${path}`, { signal }),

  create: (ns: string, path: string, payload: LockPayload) =>
    api.post<Lock>(`/ns/${ns}/~lock/${path}`, {
      ...payload,
      expires_at: payload.expires_at
        ? localDateTimeInputToUtcIso(payload.expires_at) ?? payload.expires_at
        : undefined,
    }),

  replace: (ns: string, path: string, payload: LockPayload) =>
    api.put<Lock>(`/ns/${ns}/~lock/${path}`, payload),

  delete: (ns: string, path: string) =>
    api.delete<void>(`/ns/${ns}/~lock/${path}`),
}
