export const API_UNAVAILABLE_STATUSES = new Set([502, 503, 504])

export function isApiUnavailableStatus(status: number): boolean {
  return API_UNAVAILABLE_STATUSES.has(status)
}

function getErrorStatus(error: unknown): number | undefined {
  if (typeof error !== 'object' || error === null || !('status' in error)) return undefined
  const status = (error as { status: unknown }).status
  return typeof status === 'number' ? status : undefined
}

export function isApiUnavailableError(error: unknown): boolean {
  const status = getErrorStatus(error)
  return status !== undefined && isApiUnavailableStatus(status)
}

export function formatApiErrorDetail(status: number): string {
  switch (status) {
    case 502:
      return 'The API is temporarily unavailable. The server may be starting up or restarting.'
    case 503:
      return 'The API is temporarily unavailable (service unavailable).'
    case 504:
      return 'The API did not respond in time (gateway timeout).'
    default:
      return `HTTP ${status}`
  }
}

export function formatFetchFailureMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string' && detail) return detail
  }
  if (error instanceof TypeError) {
    return 'Unable to reach the API. Check your network connection or try again shortly.'
  }
  if (error instanceof Error) return error.message
  return 'Unable to reach the API'
}
