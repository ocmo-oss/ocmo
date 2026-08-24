import type { ItemType } from '../api/types'
import { FALLBACK_PERMISSION_ACTIONS } from './permissionSchema'

export interface ItemPermissionOps {
  read: string
  write: string
  delete: string
  describe: string
  tag: string
  audit: string
  resolve?: string
}

function resolveAction(available: Set<string>, candidates: string[]): string {
  for (const candidate of candidates) {
    if (available.has(candidate)) {
      return candidate
    }
  }
  return candidates[0]!
}

export function permissionOpsForType(
  type: ItemType,
  actions: readonly string[] = FALLBACK_PERMISSION_ACTIONS,
): ItemPermissionOps {
  const available = new Set(actions)

  switch (type) {
    case 'config':
      return {
        read: resolveAction(available, ['config:read']),
        write: resolveAction(available, ['config:write']),
        delete: resolveAction(available, ['config:delete']),
        describe: resolveAction(available, ['config:describe']),
        tag: resolveAction(available, ['config:tag']),
        audit: resolveAction(available, ['config:audit']),
        resolve: resolveAction(available, ['config:resolve']),
      }
    case 'template':
      return {
        read: resolveAction(available, ['template:read']),
        write: resolveAction(available, ['template:write']),
        delete: resolveAction(available, ['template:delete']),
        describe: resolveAction(available, ['template:describe']),
        tag: resolveAction(available, ['template:tag']),
        audit: resolveAction(available, ['template:audit']),
      }
    case 'secret':
      return {
        read: resolveAction(available, ['secret:read']),
        write: resolveAction(available, ['secret:write']),
        delete: resolveAction(available, ['secret:delete']),
        describe: resolveAction(available, ['secret:describe']),
        tag: resolveAction(available, ['secret:tag']),
        audit: resolveAction(available, ['secret:audit']),
        resolve: resolveAction(available, ['secret:resolve']),
      }
    case 'resolver':
      return {
        read: resolveAction(available, ['resolver:read']),
        write: resolveAction(available, ['resolver:write']),
        delete: resolveAction(available, ['resolver:delete']),
        describe: resolveAction(available, ['config:describe']),
        tag: resolveAction(available, ['config:tag']),
        audit: resolveAction(available, ['resolver:audit']),
      }
    case 'folder':
      return {
        read: resolveAction(available, ['config:read']),
        write: resolveAction(available, ['config:write']),
        delete: resolveAction(available, ['config:delete']),
        describe: resolveAction(available, ['folder:describe']),
        tag: resolveAction(available, ['config:tag']),
        audit: resolveAction(available, ['folder:audit']),
        resolve: resolveAction(available, ['config:resolve']),
      }
  }
}

export function allPermissionOps(
  type: ItemType,
  actions: readonly string[] = FALLBACK_PERMISSION_ACTIONS,
): string[] {
  const ops = permissionOpsForType(type, actions)
  const values: string[] = [
    ops.read,
    ops.write,
    ops.delete,
    ops.describe,
    ops.tag,
    ops.audit,
  ]
  if (ops.resolve) values.push(ops.resolve)
  return values.filter((value, index, array) => array.indexOf(value) === index)
}
