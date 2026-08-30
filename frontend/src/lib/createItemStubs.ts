import type {
  ConfigNode,
  ItemType,
  ResolverNode,
  SecretNode,
} from "../api/types";
import { pathSegments } from "./paths";

export type CreateableItemType = Exclude<ItemType, "folder">;

export const CREATEABLE_ITEM_TYPES: CreateableItemType[] = [
  "config",
  "template",
  "secret",
  "resolver",
];

export function isCreateableItemType(
  value: string,
): value is CreateableItemType {
  return (CREATEABLE_ITEM_TYPES as string[]).includes(value);
}

export function normalizePathSegment(value: string): string {
  return value.trim().replace(/^\/+|\/+$/g, "");
}

export function defaultPathForParent(parentPath: string): string {
  const trimmed = normalizePathSegment(parentPath);
  return trimmed ? `${trimmed}/` : "";
}

function leafName(path: string): string {
  const segments = pathSegments(path);
  return segments[segments.length - 1] ?? path;
}

const emptyTimestamps = {
  created_at: "",
  updated_at: "",
};

export function stubConfigNode(path: string): ConfigNode {
  return {
    path,
    name: leafName(path),
    type: "config",
    version: 0,
    content: "",
    tags: [],
    updater: "",
    deleted_at: null,
    ...emptyTimestamps,
  };
}

export function stubTemplateNode(path: string): ConfigNode {
  return { ...stubConfigNode(path), type: "template" };
}

export function stubSecretNode(path: string): SecretNode {
  return {
    path,
    name: leafName(path),
    type: "secret",
    version: 0,
    tags: [],
    updater: "",
    deleted_at: null,
    ...emptyTimestamps,
  };
}

export function stubResolverNode(path: string): ResolverNode {
  return {
    path,
    name: leafName(path),
    type: "resolver",
    version: 0,
    author: "",
    token1: "",
    token1_last_used: null,
    token2: null,
    token2_last_used: null,
    configuration: "",
    ...emptyTimestamps,
  };
}
