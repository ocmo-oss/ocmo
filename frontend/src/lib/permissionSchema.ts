import type { JsonSchemaDocument } from '../api/schema'

/** Fallback when ``~config-schema/_permissions`` is not loaded yet. Mirrors API ``PERMISSION_ACTIONS``. */
export const FALLBACK_PERMISSION_ACTIONS: readonly string[] = [
  'config:read',
  'config:write',
  'config:delete',
  'config:resolve',
  'config:tag',
  'config:describe',
  'config:audit',
  'template:read',
  'template:write',
  'template:delete',
  'template:tag',
  'template:describe',
  'template:audit',
  'resolver:read',
  'resolver:write',
  'resolver:delete',
  'resolver:audit',
  'secret:read',
  'secret:write',
  'secret:delete',
  'secret:resolve',
  'secret:tag',
  'secret:describe',
  'secret:audit',
  'lock:read',
  'lock:write',
  'lock:delete',
  'folder:describe',
  'folder:audit',
  'config:*',
  'template:*',
  'resolver:*',
  'secret:*',
  'lock:*',
  '*:read',
  '*:write',
  '*:delete',
  '*:resolve',
  '*:tag',
  '*:describe',
  '*:audit',
  '*:*',
]

export const PERMISSIONS_POLICY_CONFIG_PATH = '_permissions'

const LOCK_PERMISSION_OPS = ['lock:read', 'lock:write', 'lock:delete'] as const

export function extractPermissionActionEnum(schema: JsonSchemaDocument): string[] {
  const policies = schema.properties?.policies
  if (!policies || typeof policies !== 'object' || Array.isArray(policies)) {
    return []
  }
  const items = (policies as Record<string, unknown>).items
  if (!items || typeof items !== 'object' || Array.isArray(items)) {
    return []
  }
  const actions = (items as Record<string, unknown>).properties
  if (!actions || typeof actions !== 'object' || Array.isArray(actions)) {
    return []
  }
  const actionItems = (actions as Record<string, unknown>).actions
  if (!actionItems || typeof actionItems !== 'object' || Array.isArray(actionItems)) {
    return []
  }
  const enumSchema = (actionItems as Record<string, unknown>).items
  if (!enumSchema || typeof enumSchema !== 'object' || Array.isArray(enumSchema)) {
    return []
  }
  const enumValues = (enumSchema as Record<string, unknown>).enum
  if (!Array.isArray(enumValues)) {
    return []
  }
  return enumValues.filter((value): value is string => typeof value === 'string')
}

export function lockPermissionOps(actions: readonly string[]): string[] {
  const available = new Set(actions)
  return LOCK_PERMISSION_OPS.filter(op => available.has(op))
}
