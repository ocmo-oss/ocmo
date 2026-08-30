import type {
  BuiltinNamespacePaths,
  ItemType,
  ReservedTags,
  VersionResponse,
} from "../api/types";

/** Fallback when `/api/version` has not loaded or failed. Matches API default. */
export const DEFAULT_CONFIG_METADATA_KEY = "_ocmo";

/** Fallback when `/api/version` has not loaded or failed. Matches API defaults. */
export const DEFAULT_BUILTIN_NAMESPACE_PATHS: BuiltinNamespacePaths = {
  config: ["_permissions", "_webhooks", "_git_sync"],
  secret: ["_webhooks_secret", "_git_sync_secret"],
  schema: ["_permissions.schema", "_webhooks.schema", "_git_sync.schema"],
  order: [
    "_permissions",
    "_permissions.schema",
    "_webhooks",
    "_webhooks_secret",
    "_webhooks.schema",
    "_git_sync",
    "_git_sync_secret",
    "_git_sync.schema",
  ],
};

export const DEFAULT_RESERVED_TAGS: ReservedTags = {
  config: ["latest", "stable"],
  template: ["latest"],
  secret: ["latest"],
};

export function allBuiltinNamespacePaths(
  paths: BuiltinNamespacePaths,
): Set<string> {
  return new Set([...paths.config, ...paths.secret, ...paths.schema]);
}

export function reservedTagsForItemType(
  reservedTags: ReservedTags,
  itemType: ItemType,
): readonly string[] {
  if (
    itemType === "config" ||
    itemType === "template" ||
    itemType === "secret"
  ) {
    return reservedTags[itemType];
  }
  return [];
}

export function isReservedTagName(
  tag: string,
  reservedTags: ReservedTags,
  itemType?: ItemType,
): boolean {
  if (itemType) {
    return reservedTagsForItemType(reservedTags, itemType).includes(tag);
  }
  return Object.values(reservedTags).some((tags) => tags.includes(tag));
}

export function pickVersionBootstrap(version: VersionResponse) {
  return {
    version: version.version,
    configMetadataKey: version.config_metadata_key,
    builtinNamespacePaths: version.builtin_namespace_paths,
    reservedTags: version.reserved_tags,
  };
}
