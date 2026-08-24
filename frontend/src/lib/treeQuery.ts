import type { QueryClient } from '@tanstack/react-query'
import { pathParent } from './paths'

export function invalidateItemDetailQueries(qc: QueryClient, namespace: string, itemPath: string): void {
  void qc.invalidateQueries({ queryKey: ['item', namespace, itemPath] })
  void qc.invalidateQueries({ queryKey: ['versions', namespace, itemPath] })
}

function invalidateTreeQueryKeys(
  qc: QueryClient,
  namespace: string,
  itemPaths: string[],
): void {
  void qc.invalidateQueries({ queryKey: ['tree-nav-root', namespace] })
  void qc.invalidateQueries({ queryKey: ['folder-chain', namespace] })
  void qc.invalidateQueries({ queryKey: ['tree-search', namespace] })

  for (const itemPath of itemPaths) {
    let path: string | undefined = itemPath
    while (path) {
      void qc.invalidateQueries({ queryKey: ['tree-nav', namespace, path] })
      path = pathParent(path) || undefined
    }
  }
}

export function invalidateTreeQueries(
  qc: QueryClient,
  namespace: string,
  ...itemPaths: string[]
): void {
  invalidateTreeQueryKeys(qc, namespace, itemPaths)
}

export async function refreshTreeQueries(
  qc: QueryClient,
  namespace: string,
  ...itemPaths: string[]
): Promise<void> {
  invalidateTreeQueryKeys(qc, namespace, itemPaths)

  await Promise.all([
    qc.refetchQueries({ queryKey: ['tree-nav-root', namespace], type: 'active' }),
    qc.refetchQueries({ queryKey: ['folder-chain', namespace], type: 'active' }),
    qc.refetchQueries({ queryKey: ['tree-search', namespace], type: 'active' }),
  ])
}
