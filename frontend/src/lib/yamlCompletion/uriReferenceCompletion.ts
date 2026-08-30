import type * as Monaco from "monaco-editor";
import { treeApi } from "../../api/tree";
import type { ItemType, TreeNavigationNode } from "../../api/types";
import { ITEM_TYPE_LABELS } from "../itemTypes";
import {
  formatOcmoReferenceInsert,
  isDirectoryBrowsePrefix,
  isRelativeDirectoryBrowse,
  isRelativePath,
  isUnderFolderPrefix,
  isUriReferenceSearchReady,
  pathMatchesTypedPrefix,
  resolveRelativeOcmoPath,
  searchQueryToken,
  splitOcmoReference,
} from "../ocmoPathReference";
import type { YamlCompletionContext } from "./types";
import { formatYamlScalar } from "../yamlScalar";

import { asObject, resolveRef } from "./jsonSchema";
import {
  isScalarArrayItemLine,
  arrayItemValueStartColumn,
  stripYamlScalarQuotes as stripYamlQuotes,
} from "./lineSyntax";

type JsonSchema = Record<string, unknown>;

export type OcmoUriReferenceScope = "config" | "resolver" | "resource";

const CONFIG_REFERENCE_ITEM_TYPES = new Set<ItemType>([
  "config",
  "template",
  "secret",
]);
const RESOURCE_REFERENCE_ITEM_TYPES = new Set<ItemType>([
  "config",
  "template",
  "secret",
  "resolver",
  "folder",
]);
const RESOLVER_REFERENCE_ITEM_TYPES = new Set<ItemType>(["resolver"]);

const searchCache = new Map<
  string,
  { expires: number; items: TreeNavigationNode[] }
>();
const CACHE_TTL_MS = 10_000;

function unwrapSchemaForUriRef(
  schema: JsonSchema | null,
  root: JsonSchema,
): JsonSchema | null {
  if (!schema) return null;
  const current = resolveRef(schema, root);

  if (Array.isArray(current.anyOf)) {
    for (const item of current.anyOf) {
      const candidate = unwrapSchemaForUriRef(asObject(item), root);
      if (candidate && candidate.type !== "null") return candidate;
    }
  }

  if (Array.isArray(current.oneOf)) {
    for (const item of current.oneOf) {
      const candidate = unwrapSchemaForUriRef(asObject(item), root);
      if (candidate && hasUriReferenceFormat(candidate, root)) return candidate;
    }
  }

  return current;
}

export function hasUriReferenceFormat(
  schema: JsonSchema | null,
  root: JsonSchema,
): boolean {
  const resolved = unwrapSchemaForUriRef(schema, root);
  if (!resolved) return false;
  if (resolved.format === "uri-reference") return true;

  if (Array.isArray(resolved.anyOf)) {
    return resolved.anyOf.some(
      (item) => asObject(item)?.format === "uri-reference",
    );
  }

  if (Array.isArray(resolved.oneOf)) {
    return resolved.oneOf.some(
      (item) => asObject(item)?.format === "uri-reference",
    );
  }

  return false;
}

export function resolveUriReferenceScope(
  schema: JsonSchema | null,
  root: JsonSchema,
): OcmoUriReferenceScope {
  const resolved = unwrapSchemaForUriRef(schema, root);
  const scope = resolved?.["x-ocmo-uri-reference"];
  if (scope === "resolver" || scope === "resource") return scope;
  return "config";
}

function allowedItemTypes(scope: OcmoUriReferenceScope): Set<ItemType> {
  switch (scope) {
    case "resolver":
      return RESOLVER_REFERENCE_ITEM_TYPES;
    case "resource":
      return RESOURCE_REFERENCE_ITEM_TYPES;
    default:
      return CONFIG_REFERENCE_ITEM_TYPES;
  }
}

export function isInOcmoMetadata(
  objectPath: string[],
  metadataKey: string,
): boolean {
  return objectPath.length > 0 && objectPath[0] === metadataKey;
}

function isUriReferenceCompletionContext(
  objectPath: string[],
  options: UriReferenceCompletionOptions,
): boolean {
  if (isInOcmoMetadata(objectPath, options.metadataKey)) return true;
  return Boolean(options.allowOutsideMetadata);
}

export interface UriReferenceCompletionOptions {
  namespace: string;
  configPath: string;
  metadataKey: string;
  /** Enable uri-reference completion outside the metadata block (e.g. ``_permissions``). */
  allowOutsideMetadata?: boolean;
}

export interface TypedUriReference {
  raw: string;
  pathPart: string;
  suffix: string;
  resolvedPrefix: string;
}

interface PathSuggestion {
  path: string;
  type: ItemType;
  globVariant?: boolean;
  sortOrder?: number;
}

function valueTextBeforeCursor(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  valueStartColumn: number,
): string {
  return model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: valueStartColumn,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  });
}

// isScalarArrayItemLine is imported from ./lineSyntax and re-exported via index

export function extractTypedUriReference(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): TypedUriReference | null {
  const line = model.getLineContent(position.lineNumber);
  let valueStartColumn = 0;

  if (ctx.kind === "property-value" && ctx.valuePropertyKey) {
    const colon = line.indexOf(":");
    if (colon < 0) return null;
    valueStartColumn = colon + 2;
    while (
      valueStartColumn <= line.length &&
      /\s/.test(line[valueStartColumn - 1] ?? "")
    ) {
      valueStartColumn += 1;
    }
    const leading = line[valueStartColumn - 1];
    if (leading === '"' || leading === "'") {
      valueStartColumn += 1;
    }
  } else if (ctx.kind === "array-item") {
    const start = arrayItemValueStartColumn(line);
    if (start === null) return null;
    valueStartColumn = start;
    if (!isScalarArrayItemLine(line)) return null;
  } else {
    return null;
  }

  const raw = stripYamlQuotes(
    valueTextBeforeCursor(model, position, valueStartColumn),
  );
  const { pathPart, suffix } = raw
    ? splitOcmoReference(raw)
    : { pathPart: "", suffix: "" };
  return { raw, pathPart, suffix, resolvedPrefix: "" };
}

export function uriReferenceCompletionRange(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): Monaco.IRange | null {
  const line = model.getLineContent(position.lineNumber);
  let valueStartColumn = position.column;

  if (ctx.kind === "property-value" && ctx.valuePropertyKey) {
    const colon = line.indexOf(":");
    if (colon < 0) return null;
    valueStartColumn = colon + 2;
    while (
      valueStartColumn <= line.length &&
      /\s/.test(line[valueStartColumn - 1] ?? "")
    ) {
      valueStartColumn += 1;
    }
    const leading = line[valueStartColumn - 1];
    if (leading === '"' || leading === "'") {
      valueStartColumn += 1;
    }
  } else if (ctx.kind === "array-item") {
    const start = arrayItemValueStartColumn(line);
    if (start === null || !isScalarArrayItemLine(line)) return null;
    valueStartColumn = start;
  } else {
    return null;
  }

  return {
    startLineNumber: position.lineNumber,
    startColumn: valueStartColumn,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  };
}

function withResolvedPrefix(
  typed: TypedUriReference,
  configPath: string,
): TypedUriReference {
  return {
    ...typed,
    resolvedPrefix: resolveRelativeOcmoPath(configPath, typed.pathPart),
  };
}

function filterReferenceItems(
  items: TreeNavigationNode[],
  resolvedPrefix: string,
  currentConfigPath: string,
  scope: OcmoUriReferenceScope,
  options: { underPrefixOnly?: boolean } = {},
): TreeNavigationNode[] {
  const allowed = allowedItemTypes(scope);
  return items
    .filter((item) => allowed.has(item.type))
    .filter((item) => item.path !== currentConfigPath)
    .filter((item) =>
      options.underPrefixOnly
        ? isUnderFolderPrefix(item.path, resolvedPrefix)
        : pathMatchesTypedPrefix(item.path, resolvedPrefix),
    )
    .sort((a, b) => a.path.localeCompare(b.path));
}

function isDirectChildPath(childPath: string, folderPath: string): boolean {
  if (!childPath.startsWith(`${folderPath}/`)) return false;
  const remainder = childPath.slice(folderPath.length + 1);
  return remainder.length > 0 && !remainder.includes("/");
}

function expandPathSuggestions(
  items: TreeNavigationNode[],
  scope: OcmoUriReferenceScope,
): PathSuggestion[] {
  const sorted = [...items].sort((a, b) => a.path.localeCompare(b.path));
  if (scope !== "resource") {
    return sorted.map((item, index) => ({
      path: item.path,
      type: item.type,
      sortOrder: index,
    }));
  }

  const folders = sorted.filter((item) => item.type === "folder");
  const nonFolders = sorted.filter((item) => item.type !== "folder");
  const ordered: PathSuggestion[] = [];
  let sortOrder = 0;
  const placed = new Set<string>();

  const place = (suggestion: PathSuggestion) => {
    if (placed.has(suggestion.path)) return;
    ordered.push({ ...suggestion, sortOrder: sortOrder++ });
    placed.add(suggestion.path);
  };

  for (const folder of folders) {
    place({ path: folder.path, type: folder.type });
    place({ path: `${folder.path}/**`, type: folder.type, globVariant: true });
    for (const item of nonFolders) {
      if (isDirectChildPath(item.path, folder.path)) {
        place({ path: item.path, type: item.type });
      }
    }
  }

  for (const item of nonFolders) {
    place({ path: item.path, type: item.type });
  }

  return ordered;
}

function resourceSuggestionSortText(suggestion: PathSuggestion): string {
  const order = suggestion.sortOrder ?? 0;
  if (suggestion.globVariant) {
    return `${order.toString().padStart(6, "0")}:glob`;
  }
  if (suggestion.type === "folder") {
    return `${order.toString().padStart(6, "0")}:folder:${suggestion.path}`;
  }
  return `${order.toString().padStart(6, "0")}:${suggestion.path}`;
}

async function listFolderDescendants(
  namespace: string,
  folderPath: string,
  signal?: AbortSignal,
): Promise<TreeNavigationNode[]> {
  try {
    const nav = await treeApi.navigate(
      namespace,
      folderPath || null,
      { recursive: true, limit: 100 },
      signal,
    );
    return nav.children;
  } catch {
    const results = await treeApi.search(
      namespace,
      folderPath || null,
      { limit: 100 },
      signal,
    );
    return results.filter((item) => isUnderFolderPrefix(item.path, folderPath));
  }
}

async function listRootItems(
  namespace: string,
  signal?: AbortSignal,
): Promise<TreeNavigationNode[]> {
  const nav = await treeApi.navigate(namespace, null, { limit: 100 }, signal);
  return nav.children;
}

function resolvedPrefixParts(resolvedPrefix: string): {
  parent: string;
  partial: string;
} {
  const normalized = resolvedPrefix.replace(/\/+$/, "");
  const slash = normalized.lastIndexOf("/");
  if (slash < 0) {
    return { parent: "", partial: normalized };
  }
  return {
    parent: normalized.slice(0, slash),
    partial: normalized.slice(slash + 1),
  };
}

async function listItemsMatchingPrefix(
  namespace: string,
  resolvedPrefix: string,
  currentConfigPath: string,
  scope: OcmoUriReferenceScope,
  signal?: AbortSignal,
): Promise<TreeNavigationNode[]> {
  if (!isUriReferenceSearchReady(resolvedPrefix)) return [];

  const { parent } = resolvedPrefixParts(resolvedPrefix);
  let candidates: TreeNavigationNode[];
  try {
    candidates = parent
      ? await listFolderDescendants(namespace, parent, signal)
      : await listRootItems(namespace, signal);
  } catch {
    return [];
  }

  return filterReferenceItems(
    candidates,
    resolvedPrefix,
    currentConfigPath,
    scope,
  );
}

async function searchReferenceItems(
  namespace: string,
  typedPathPart: string,
  resolvedPrefix: string,
  currentConfigPath: string,
  scope: OcmoUriReferenceScope,
  signal?: AbortSignal,
  absoluteOnly = false,
): Promise<TreeNavigationNode[]> {
  const allowed = allowedItemTypes(scope);

  if (!resolvedPrefix && !typedPathPart) {
    try {
      const children = await listRootItems(namespace, signal);
      return filterReferenceItems(children, "", currentConfigPath, scope);
    } catch {
      return [];
    }
  }

  if (!absoluteOnly && isDirectoryBrowsePrefix(typedPathPart, resolvedPrefix)) {
    try {
      const descendants = await listFolderDescendants(
        namespace,
        resolvedPrefix,
        signal,
      );
      return filterReferenceItems(
        descendants,
        resolvedPrefix,
        currentConfigPath,
        scope,
        {
          underPrefixOnly: true,
        },
      );
    } catch {
      return [];
    }
  }

  try {
    const prefixMatches = await listItemsMatchingPrefix(
      namespace,
      resolvedPrefix,
      currentConfigPath,
      scope,
      signal,
    );
    if (prefixMatches.length > 0) {
      return prefixMatches;
    }
  } catch {
    // Fall through to search API.
  }

  if (!isUriReferenceSearchReady(resolvedPrefix)) return [];

  const token = searchQueryToken(resolvedPrefix);
  if (!token) return [];

  const cacheKey = `${namespace}:${scope}:${token}`;
  const cached = searchCache.get(cacheKey);
  if (cached && cached.expires > Date.now()) {
    return filterReferenceItems(
      cached.items,
      resolvedPrefix,
      currentConfigPath,
      scope,
    );
  }

  const results = await treeApi.search(
    namespace,
    null,
    { q: token, limit: 50 },
    signal,
  );

  const referenceItems = results.filter((item) => allowed.has(item.type));
  searchCache.set(cacheKey, {
    expires: Date.now() + CACHE_TTL_MS,
    items: referenceItems,
  });
  return filterReferenceItems(
    referenceItems,
    resolvedPrefix,
    currentConfigPath,
    scope,
  );
}

function formatArrayItemUriInsertText(
  line: string,
  insertText: string,
): string {
  const match = line.match(/^(\s*-\s*)(.*)$/);
  if (!match || match[1].endsWith(" ")) return insertText;
  return insertText.startsWith(" ") ? insertText : ` ${insertText}`;
}

function requiresAbsoluteReferences(
  options: UriReferenceCompletionOptions,
  scope: OcmoUriReferenceScope,
): boolean {
  return (
    options.configPath === "_permissions" &&
    (scope === "resolver" || scope === "resource")
  );
}

function formatReferenceInsertText(
  options: UriReferenceCompletionOptions,
  scope: OcmoUriReferenceScope,
  absolutePath: string,
  typedPathPart: string,
  suffix: string,
): string {
  if (requiresAbsoluteReferences(options, scope)) {
    return `${absolutePath}${suffix}`;
  }
  return formatOcmoReferenceInsert(
    options.configPath,
    absolutePath,
    typedPathPart,
    suffix,
  );
}

function shouldSuppressUriReferenceSuggestions(
  suggestions: PathSuggestion[],
  resolvedPrefix: string,
): boolean {
  if (suggestions.length === 0) return true;
  if (suggestions.length === 1 && suggestions[0].path === resolvedPrefix)
    return true;
  return false;
}

export function shouldSuggestUriReferences(
  schema: JsonSchema | null,
  root: JsonSchema,
  ctx: YamlCompletionContext,
  options: UriReferenceCompletionOptions,
  typed: TypedUriReference | null,
): boolean {
  if (!isUriReferenceCompletionContext(ctx.objectPath, options)) return false;
  if (!hasUriReferenceFormat(schema, root)) return false;
  if (ctx.kind !== "property-value" && ctx.kind !== "array-item") return false;

  const scope = resolveUriReferenceScope(schema, root);
  const absoluteOnly = requiresAbsoluteReferences(options, scope);
  const allowEmptyBrowse =
    Boolean(options.allowOutsideMetadata) &&
    (scope === "resource" || scope === "resolver");

  if (!typed || !typed.pathPart) {
    return allowEmptyBrowse;
  }

  if (absoluteOnly && isRelativePath(typed.pathPart)) {
    return false;
  }

  const resolvedPrefix = resolveRelativeOcmoPath(
    options.configPath,
    typed.pathPart,
  );
  return (
    isUriReferenceSearchReady(resolvedPrefix) ||
    (!absoluteOnly && isRelativeDirectoryBrowse(typed.pathPart))
  );
}

const SECRET_REFERENCE_ITEM_TYPES = new Set<ItemType>(["secret"]);

async function searchSecretReferenceItems(
  namespace: string,
  pathPart: string,
  resolvedPrefix: string,
  currentConfigPath: string,
  signal?: AbortSignal,
  absoluteOnly = false,
): Promise<TreeNavigationNode[]> {
  const items = await searchReferenceItems(
    namespace,
    pathPart,
    resolvedPrefix,
    currentConfigPath,
    "config",
    signal,
    absoluteOnly,
  );
  return items.filter((item) => SECRET_REFERENCE_ITEM_TYPES.has(item.type));
}

export function shouldSuggestSecretPathReferences(
  options: UriReferenceCompletionOptions,
  typed: TypedUriReference | null,
): boolean {
  if (!typed || !typed.pathPart) {
    return true;
  }
  const resolvedPrefix = resolveRelativeOcmoPath(
    options.configPath,
    typed.pathPart,
  );
  return (
    isUriReferenceSearchReady(resolvedPrefix) ||
    isRelativeDirectoryBrowse(typed.pathPart)
  );
}

export async function buildSecretPathSuggestions(
  monaco: typeof Monaco,
  ctx: YamlCompletionContext,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  options: Pick<UriReferenceCompletionOptions, "namespace" | "configPath">,
  signal?: AbortSignal,
): Promise<Monaco.languages.CompletionItem[]> {
  const typed = extractTypedUriReference(model, position, ctx) ?? {
    raw: "",
    pathPart: "",
    suffix: "",
    resolvedPrefix: "",
  };
  if (
    !shouldSuggestSecretPathReferences(
      options as UriReferenceCompletionOptions,
      typed,
    )
  ) {
    return [];
  }

  const resolved = withResolvedPrefix(typed, options.configPath);
  const range = uriReferenceCompletionRange(model, position, ctx);
  if (!range) return [];

  let items: TreeNavigationNode[];
  try {
    items = await searchSecretReferenceItems(
      options.namespace,
      resolved.pathPart,
      resolved.resolvedPrefix,
      options.configPath,
      signal,
    );
  } catch {
    return [];
  }

  if (signal?.aborted) return [];

  const suggestions = expandPathSuggestions(items, "config").filter(
    (suggestion) => suggestion.type === "secret",
  );
  if (suggestions.length === 0) return [];
  if (
    shouldSuppressUriReferenceSuggestions(suggestions, resolved.resolvedPrefix)
  ) {
    return [];
  }

  const uriOptions = options as UriReferenceCompletionOptions;
  return suggestions.map((suggestion) => {
    const insertText = formatYamlScalar(
      formatReferenceInsertText(
        uriOptions,
        "config",
        suggestion.path,
        resolved.pathPart,
        resolved.suffix,
      ),
    );
    const typeLabel = ITEM_TYPE_LABELS[suggestion.type];
    return {
      label: { label: suggestion.path, description: typeLabel },
      kind: monaco.languages.CompletionItemKind.Reference,
      insertText,
      range,
      filterText: `${insertText} ${suggestion.path}`,
      sortText: resourceSuggestionSortText(suggestion),
      detail: typeLabel,
      documentation: `${typeLabel} · ${suggestion.path}`,
    };
  });
}

export async function buildUriReferenceSuggestions(
  monaco: typeof Monaco,
  schema: JsonSchema,
  root: JsonSchema,
  ctx: YamlCompletionContext,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  options: UriReferenceCompletionOptions,
  signal?: AbortSignal,
): Promise<Monaco.languages.CompletionItem[]> {
  const typed = extractTypedUriReference(model, position, ctx) ?? {
    raw: "",
    pathPart: "",
    suffix: "",
    resolvedPrefix: "",
  };
  if (!shouldSuggestUriReferences(schema, root, ctx, options, typed)) {
    return [];
  }

  const scope = resolveUriReferenceScope(schema, root);
  const absoluteOnly = requiresAbsoluteReferences(options, scope);
  const resolved = withResolvedPrefix(typed, options.configPath);
  const range = uriReferenceCompletionRange(model, position, ctx);
  if (!range) return [];

  let items: TreeNavigationNode[];
  try {
    items = await searchReferenceItems(
      options.namespace,
      resolved.pathPart,
      resolved.resolvedPrefix,
      options.configPath,
      scope,
      signal,
      absoluteOnly,
    );
  } catch {
    return [];
  }

  if (signal?.aborted) return [];

  const suggestions = expandPathSuggestions(items, scope);
  if (suggestions.length === 0) return [];
  if (
    shouldSuppressUriReferenceSuggestions(suggestions, resolved.resolvedPrefix)
  ) {
    return [];
  }

  return suggestions.map((suggestion) => {
    let insertText = formatYamlScalar(
      formatReferenceInsertText(
        options,
        scope,
        suggestion.path,
        resolved.pathPart,
        resolved.suffix,
      ),
    );
    if (ctx.kind === "array-item") {
      insertText = formatArrayItemUriInsertText(
        model.getLineContent(position.lineNumber),
        insertText,
      );
    }
    const typeLabel = suggestion.globVariant
      ? `${ITEM_TYPE_LABELS[suggestion.type]} glob`
      : ITEM_TYPE_LABELS[suggestion.type];
    const filterText = `${insertText} ${suggestion.path}`;
    return {
      label: { label: suggestion.path, description: typeLabel },
      kind: monaco.languages.CompletionItemKind.Reference,
      insertText,
      range,
      filterText,
      sortText: resourceSuggestionSortText(suggestion),
      detail: typeLabel,
      documentation: suggestion.globVariant
        ? `Folder glob · matches descendants under ${suggestion.path.slice(0, -3)}`
        : `${typeLabel} · ${suggestion.path}`,
    };
  });
}

export function __testingUriReference() {
  return {
    searchCache,
    extractTypedUriReference,
    withResolvedPrefix,
    expandPathSuggestions,
    isDirectChildPath,
    listItemsMatchingPrefix,
    resolvedPrefixParts,
    requiresAbsoluteReferences,
    formatReferenceInsertText,
    resolveUriReferenceScope,
  };
}
