import { env } from '../env'
import {
  formatApiErrorDetail,
  formatFetchFailureMessage,
  isApiUnavailableStatus,
} from '../lib/apiAvailability'
import { parseApiErrorBody } from '../lib/apiErrorFormat'
import { useHealthStore } from '../store/health'

function parseErrorDetail(status: number, body: string): string {
  if (isApiUnavailableStatus(status)) {
    return formatApiErrorDetail(status)
  }

  return parseApiErrorBody(status, body)
}

function markApiAvailability(status: number, detail: string): void {
  if (isApiUnavailableStatus(status)) {
    useHealthStore.getState().setHealthError(detail)
    return
  }
  useHealthStore.getState().clearAvailabilityError()
}

function markApiReachable(): void {
  useHealthStore.getState().clearAvailabilityError()
}

function markApiUnreachable(error: unknown): never {
  const detail = formatFetchFailureMessage(error)
  useHealthStore.getState().setHealthError(detail)
  if (error instanceof Error) throw error
  throw new Error(detail)
}

function parseAuditEventId(body: Record<string, unknown>): string | undefined {
  const raw = body['audit_event_id']
  if (raw == null || raw === '') return undefined
  return String(raw)
}

function throwApiError(status: number, body: string): never {
  const detail = parseErrorDetail(status, body)
  let auditEventId: string | undefined
  if (!isApiUnavailableStatus(status)) {
    try {
      const j = JSON.parse(body) as Record<string, unknown>
      auditEventId = parseAuditEventId(j)
    } catch {
      // keep default
    }
  }
  markApiAvailability(status, detail)
  throw new ApiError(status, body, detail, auditEventId)
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
    public readonly detail: string,
    public readonly auditEventId?: string,
  ) {
    super(detail)
    this.name = 'ApiError'
  }
}

/** Token provider — set by auth layer. */
let _getToken: (() => string | null) | null = null

export function setTokenProvider(fn: () => string | null): void {
  _getToken = fn
}

export function clearTokenProvider(): void {
  _getToken = null
}

/** Rewrite absolute API artifact URLs to same-origin paths for proxy compatibility. */
export function normalizeArtifactUrl(url: string): string {
  try {
    const parsed = new URL(url, window.location.origin)
    if (parsed.pathname.startsWith('/api/')) {
      return `${parsed.pathname}${parsed.search}`
    }
  } catch {
    // keep original url
  }
  return url
}

/** Fetch text from a signed resolve download URL (requires auth). */
export async function fetchAuthenticatedText(url: string, signal?: AbortSignal): Promise<string> {
  const headers: Record<string, string> = {}
  const token = _getToken?.()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(normalizeArtifactUrl(url), { headers, signal })
  } catch (error) {
    markApiUnreachable(error)
  }
  if (!res.ok) {
    const body = await res.text()
    throwApiError(res.status, body)
  }
  markApiReachable()
  return res.text()
}

async function request<T>(
  method: string,
  path: string,
  options: {
    body?: unknown
    rawBody?: string
    contentType?: string
    signal?: AbortSignal
    params?: Record<string, string | number | boolean | undefined | null>
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {}

  const token = _getToken?.()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let url = `${env.apiBase}/api/v1${path}`

  if (options.params) {
    const qs = new URLSearchParams()
    for (const [k, v] of Object.entries(options.params)) {
      if (v !== undefined && v !== null) qs.set(k, String(v))
    }
    const s = qs.toString()
    if (s) url += `?${s}`
  }

  let fetchBody: BodyInit | undefined
  if (options.rawBody !== undefined) {
    fetchBody = options.rawBody
    headers['Content-Type'] = options.contentType ?? 'text/plain'
  } else if (options.body !== undefined) {
    fetchBody = JSON.stringify(options.body)
    headers['Content-Type'] = 'application/json'
  }

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body: fetchBody,
      signal: options.signal,
    })
  } catch (error) {
    markApiUnreachable(error)
  }

  if (!res.ok) {
    const body = await res.text()
    throwApiError(res.status, body)
  }

  markApiReachable()

  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

// Convenience wrappers
export const api = {
  get: <T>(path: string, options?: Parameters<typeof request>[2]) =>
    request<T>('GET', path, options),
  post: <T>(path: string, body?: unknown, options?: Omit<Parameters<typeof request>[2], 'body'>) =>
    request<T>('POST', path, { ...options, body }),
  put: <T>(path: string, body?: unknown, options?: Omit<Parameters<typeof request>[2], 'body'>) =>
    request<T>('PUT', path, { ...options, body }),
  patch: <T>(path: string, body?: unknown, options?: Omit<Parameters<typeof request>[2], 'body'>) =>
    request<T>('PATCH', path, { ...options, body }),
  delete: <T>(path: string, options?: Parameters<typeof request>[2]) =>
    request<T>('DELETE', path, options),
}

/** Raw fetch used for non-JSON operations (YAML/text upload). */
export function rawPut(path: string, content: string, signal?: AbortSignal): Promise<unknown> {
  return request<unknown>('PUT', path, { rawBody: content, contentType: 'text/plain', signal })
}

export function rawPost(path: string, content: string, signal?: AbortSignal): Promise<unknown> {
  return request<unknown>('POST', path, { rawBody: content, contentType: 'text/plain', signal })
}

/** System endpoints — no /api/v1 prefix. */
export async function fetchHealth(): Promise<import('./types').HealthResponse> {
  let res: Response
  try {
    res = await fetch(`${env.apiBase}/api/health`)
  } catch (error) {
    markApiUnreachable(error)
  }
  if (!res.ok) {
    const body = await res.text()
    throwApiError(res.status, body)
  }
  const health = await res.json() as import('./types').HealthResponse
  markApiReachable()
  useHealthStore.getState().setHealth(health)
  return health
}

export async function fetchVersion(): Promise<import('./types').VersionResponse> {
  let res: Response
  try {
    res = await fetch(`${env.apiBase}/api/version`)
  } catch (error) {
    markApiUnreachable(error)
  }
  if (!res.ok) {
    const body = await res.text()
    throwApiError(res.status, body)
  }
  markApiReachable()
  return res.json() as Promise<import('./types').VersionResponse>
}
