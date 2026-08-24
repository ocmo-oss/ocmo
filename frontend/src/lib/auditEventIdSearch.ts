const UUID_PATTERN = String.raw`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`
const UUID_RE = new RegExp(UUID_PATTERN, 'i')
const COMPLETE_UUID_RE = new RegExp(`^${UUID_PATTERN}$`, 'i')
const AUDIT_EVENT_ID_LINE_RE = new RegExp(
  String.raw`audit\s+event\s+id\s*:\s*(${UUID_PATTERN})`,
  'i',
)

function findAuditEventIdLine(value: string): string | undefined {
  for (const line of value.split(/\r?\n/)) {
    const match = line.match(AUDIT_EVENT_ID_LINE_RE)
    if (match) return match[1]
  }
  return undefined
}

function findUniqueUuid(value: string): string | undefined {
  const matches = value.match(new RegExp(UUID_PATTERN, 'gi'))
  if (!matches || matches.length !== 1) return undefined
  return matches[0]
}

/** Normalize audit event ID search input, including full notification paste. */
export function extractAuditEventIdInput(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''

  const fromAuditLine = findAuditEventIdLine(trimmed)
  if (fromAuditLine) return fromAuditLine

  if (UUID_RE.test(trimmed) && trimmed.match(new RegExp(UUID_PATTERN, 'gi'))?.length === 1) {
    return trimmed.match(UUID_RE)![0]
  }

  const isMultiline = /\r?\n/.test(trimmed)
  if (isMultiline) {
    const unique = findUniqueUuid(trimmed)
    if (unique) return unique
    return ''
  }

  return trimmed
}

export function isCompleteAuditEventId(value: string | undefined): boolean {
  if (!value?.trim()) return false
  return COMPLETE_UUID_RE.test(value.trim())
}

export function applyAuditEventIdFilter<T extends { event_id?: string }>(filters: T): T {
  const eventId = filters.event_id
  if (eventId === undefined || eventId === '') return filters
  if (isCompleteAuditEventId(eventId)) return filters
  const { event_id: _removed, ...rest } = filters
  return rest as T
}
