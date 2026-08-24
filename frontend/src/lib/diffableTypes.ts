import type { ItemType } from '../api/types'

const DIFFABLE_TYPES = new Set<ItemType>(['config', 'template', 'secret', 'resolver'])

const VERSIONED_DIFFABLE_TYPES = new Set<ItemType>(['config', 'template', 'secret'])

export function isDiffableType(
  type: ItemType | null,
): type is Extract<ItemType, 'config' | 'template' | 'secret' | 'resolver'> {
  return type !== null && DIFFABLE_TYPES.has(type)
}

export function hasDiffVersionHistory(type: ItemType | null): boolean {
  return type !== null && VERSIONED_DIFFABLE_TYPES.has(type)
}
