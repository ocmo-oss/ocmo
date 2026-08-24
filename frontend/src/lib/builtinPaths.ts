import { useHealthStore } from '../store/health'
import {
  allBuiltinNamespacePaths,
  DEFAULT_BUILTIN_NAMESPACE_PATHS,
} from '../store/versionBootstrap'

export const NAMESPACE_CONFIGS_FOLDER_LABEL = 'Namespace configs'

export function normalizeTreePath(path: string): string {
  return path.trim().replace(/^\/+|\/+$/g, '')
}

function builtinPathsState() {
  return useHealthStore.getState().builtinNamespacePaths
}

export function getBuiltinNamespacePaths() {
  return builtinPathsState()
}

export function permissionsConfigPath(): string {
  const paths = builtinPathsState()
  return paths.config.find(path => path === '_permissions') ?? '_permissions'
}

export function isBuiltinNamespacePath(path: string): boolean {
  const normalized = normalizeTreePath(path)
  return allBuiltinNamespacePaths(builtinPathsState()).has(normalized)
}

export function isBuiltinNamespaceSchemaPath(path: string): boolean {
  const normalized = normalizeTreePath(path)
  return new Set(builtinPathsState().schema).has(normalized)
}

export function partitionBuiltinChildren<T extends { path: string }>(children: T[]): {
  builtin: T[]
  regular: T[]
} {
  const paths = builtinPathsState()
  const allBuiltin = allBuiltinNamespacePaths(paths)
  const order = paths.order
  const builtin: T[] = []
  const regular: T[] = []
  for (const child of children) {
    if (allBuiltin.has(normalizeTreePath(child.path))) {
      builtin.push(child)
    } else {
      regular.push(child)
    }
  }
  builtin.sort(
    (a, b) => order.indexOf(normalizeTreePath(a.path))
      - order.indexOf(normalizeTreePath(b.path)),
  )
  return { builtin, regular }
}

/** Pre-bootstrap fallback for tests and very early imports. */
export const FALLBACK_BUILTIN_NAMESPACE_PATHS = DEFAULT_BUILTIN_NAMESPACE_PATHS
