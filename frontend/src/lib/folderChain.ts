import { treeApi } from "../api/tree";
import type { TreeNavigationNode } from "../api/types";

export interface FolderChainSegment {
  name: string;
  path: string;
}

export interface FolderChainResult {
  segments: FolderChainSegment[];
  terminal: TreeNavigationNode;
  children: TreeNavigationNode[];
}

export async function resolveFolderChain(
  namespace: string,
  start: TreeNavigationNode,
  signal?: AbortSignal,
): Promise<FolderChainResult> {
  const segments: FolderChainSegment[] = [
    { name: start.name, path: start.path },
  ];
  let terminal = start;
  let children: TreeNavigationNode[] = [];

  for (;;) {
    const data = await treeApi.navigate(
      namespace,
      terminal.path,
      { limit: 200 },
      signal,
    );
    children = data.children;
    if (children.length === 1 && children[0].type === "folder") {
      terminal = children[0];
      segments.push({ name: terminal.name, path: terminal.path });
      continue;
    }
    break;
  }

  return { segments, terminal, children };
}
