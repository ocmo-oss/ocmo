export function formatServerErrorDetail(payload: Record<string, unknown>): string {
  const raw = payload.errors ?? payload.error ?? payload.detail
  if (Array.isArray(raw)) {
    return raw.map((item) => String(item)).join('\n')
  }
  if (raw != null && raw !== '') {
    return String(raw)
  }
  return 'Request failed'
}

export function parseApiErrorBody(status: number, body: string): string {
  try {
    const payload = JSON.parse(body) as Record<string, unknown>
    return formatServerErrorDetail(payload)
  } catch {
    return `HTTP ${status}`
  }
}
