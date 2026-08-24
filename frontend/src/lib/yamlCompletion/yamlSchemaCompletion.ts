import type * as Monaco from 'monaco-editor'
import {
  buildParameterPlaceholderSuggestions,
  shouldSuggestParameterPlaceholders,
  type ParameterCompletionOptions,
} from './ocmoParameterCompletion'
import {
  buildParameterProjectedValueSuggestions,
  canSuggestInParameterDeclarationObject,
  detectOcmoParameterDeclarationContext,
  detectOcmoParameterValueContext,
  existingKeysInYamlObject,
  isAtParameterFieldRow,
  readOcmoParameterType,
  resolveParameterDeclarationSchema,
  shouldSuggestParameterDeclarationFields,
  shouldSuggestParameterValue,
} from './ocmoParameterDeclarationCompletion'
import {
  buildSecretPathSuggestions,
  buildUriReferenceSuggestions,
  extractTypedUriReference,
  hasUriReferenceFormat,
  isInOcmoMetadata,
  shouldSuggestUriReferences,
  type UriReferenceCompletionOptions,
} from './uriReferenceCompletion'
import type { SchemaPathOptions, YamlCompletionContext } from './types'
import {
  buildJsonSchemaRootSnippetSuggestion,
  isJsonSchemaDocumentRootContext,
  isJsonSchemaDocumentSchema,
  resolveJsonSchemaTargetSchema,
  shouldOfferJsonSchemaRootSnippet,
} from './jsonSchemaCompletion'
import { escapeMonacoSnippetDollars } from './monacoSnippet'
import {
  formatYamlScalarSnippet,
  formatYamlScalarValue,
  yamlScalarKindFromSchema,
  type YamlScalarKind,
} from '../yamlScalar'
import {
  type JsonSchema,
  asObject,
  resolveRef,
  oneOfBranches,
  hasOneOf,
  oneOfVariantLabel,
  inheritSchemaMetadata,
  unwrapSchema,
} from './jsonSchema'
import {
  lineKey,
  lineArrayItemKey,
  isArrayItemLine,
  isEmptyScalarArrayItemLine,
  isScalarArrayItemLine,
  arrayItemLinePrefix,
  needsLeadingSpaceAfterArrayDash,
  formatScalarArrayItemInsertText,
  bodyLineLeadingSpaces,
  arrayItemCount,
  stripYamlScalarQuotes,
} from './lineSyntax'


function indent(level: number): string {
  return '  '.repeat(level)
}


/** Per-root WeakMap memo for unwrapSchemaForBuild. */
const unwrapForBuildCache = new WeakMap<JsonSchema, WeakMap<JsonSchema, JsonSchema | null>>()

/** Resolves schema for nested snippet generation (picks first oneOf branch). Memoized per root. */
function unwrapSchemaForBuild(schema: JsonSchema | null, root: JsonSchema): JsonSchema | null {
  if (!schema) return null
  let inner = unwrapForBuildCache.get(root)
  if (!inner) {
    inner = new WeakMap()
    unwrapForBuildCache.set(root, inner)
  }
  if (inner.has(schema)) return inner.get(schema) ?? null
  const result = resolveSchemaForBuild(schema, root, '', DEFAULT_SNIPPET_OPTIONS)
  inner.set(schema, result)
  return result
}

type SnippetDepth = 'required' | 'full'

interface SnippetBuildOptions {
  depth: SnippetDepth
  oneOfChoices: Map<string, number>
}

const DEFAULT_SNIPPET_OPTIONS: SnippetBuildOptions = {
  depth: 'required',
  oneOfChoices: new Map(),
}

interface OneOfSite {
  path: string
  branchCount: number
}

function childSchemaPath(parent: string, segment: string): string {
  return parent ? `${parent}.${segment}` : segment
}

function resolveSchemaForBuild(
  schema: JsonSchema | null,
  root: JsonSchema,
  oneOfPath: string,
  options: SnippetBuildOptions,
): JsonSchema | null {
  if (!schema) return null
  const current = unwrapSchema(schema, root)
  if (!current) return null

  const branches = oneOfBranches(current, root)
  if (branches.length > 0) {
    const idx = options.oneOfChoices.get(oneOfPath) ?? 0
    const branch = branches[Math.min(Math.max(idx, 0), branches.length - 1)]
    return resolveSchemaForBuild(branch, root, oneOfPath, options)
  }

  return current
}

function collectOneOfSites(
  schema: JsonSchema,
  root: JsonSchema,
  path: string,
  sites: OneOfSite[],
): void {
  const resolved = unwrapSchema(schema, root)
  if (!resolved) return

  const branches = oneOfBranches(resolved, root)
  if (branches.length > 1) {
    if (!sites.some(site => site.path === path)) {
      sites.push({ path, branchCount: branches.length })
    }
    for (const branch of branches) {
      descendSchemaForOneOfCollection(branch, root, path, sites)
    }
    return
  }

  descendSchemaForOneOfCollection(resolved, root, path, sites)
}

function descendSchemaForOneOfCollection(
  schema: JsonSchema,
  root: JsonSchema,
  path: string,
  sites: OneOfSite[],
): void {
  const resolved = unwrapSchema(schema, root)
  if (!resolved) return

  if (isObjectSchema(resolved)) {
    const properties = asObject(resolved.properties) ?? {}
    for (const [key, raw] of Object.entries(properties)) {
      collectOneOfSites(asObject(raw) ?? {}, root, childSchemaPath(path, key), sites)
    }
  }

  if (isArraySchema(resolved)) {
    const items = itemSchemaOf(resolved)
    if (items) {
      collectOneOfSites(items, root, childSchemaPath(path, 'items'), sites)
    }
  }
}

const CARTESIAN_COMBO_LIMIT = 32

function cartesianOneOfChoices(
  sites: OneOfSite[],
  _limit = CARTESIAN_COMBO_LIMIT,
): Map<string, number>[] {
  if (sites.length === 0) return [new Map()]

  const [first, ...rest] = sites
  const restCombos = cartesianOneOfChoices(rest, _limit)
  const combos: Map<string, number>[] = []

  for (let i = 0; i < first.branchCount; i++) {
    for (const restCombo of restCombos) {
      if (combos.length >= _limit) return combos
      const combo = new Map(restCombo)
      combo.set(first.path, i)
      combos.push(combo)
    }
  }

  return combos
}

function navigateToSchemaPath(
  schema: JsonSchema,
  root: JsonSchema,
  path: string,
): JsonSchema | null {
  if (!path) return unwrapSchema(schema, root)

  let current: JsonSchema | null = schema
  for (const segment of path.split('.')) {
    current = unwrapSchema(current, root)
    if (!current) return null

    if (segment === 'items') {
      if (!isArraySchema(current)) return null
      current = itemSchemaOf(current)
      continue
    }

    const properties = asObject(current.properties)
    if (properties && segment in properties) {
      current = asObject(properties[segment])
      continue
    }

    return null
  }

  return unwrapSchema(current, root)
}

function snippetVariantLabel(
  schema: JsonSchema,
  root: JsonSchema,
  schemaPath: string,
  depth: SnippetDepth,
  oneOfChoices: Map<string, number>,
): string {
  const parts: string[] = []
  const sortedChoices = [...oneOfChoices.entries()].sort(([a], [b]) => a.localeCompare(b))

  for (const [path, index] of sortedChoices) {
    const atPath = navigateToSchemaPath(schema, root, path)
    const branches = oneOfBranches(atPath, root)
    const branch = branches[index]
    if (branch) parts.push(oneOfVariantLabel(branch, index))
  }

  if (parts.length === 0) {
    const resolved = resolveSchemaForBuild(schema, root, schemaPath, {
      depth,
      oneOfChoices: new Map(),
    })
    if (resolved && typeof resolved.title === 'string' && resolved.title.trim()) {
      parts.push(resolved.title.trim())
    } else {
      parts.push('new item')
    }
  }

  parts.push(depth === 'required' ? 'required fields' : 'all fields')
  return parts.join(' · ')
}

/** Centralised sortText tier table. All sort strings are defined here. */
const SORT_TEXT = {
  /** Enum/discriminator values: sort before properties (`!` < `0` < `z`). */
  enumValue: (index: number, label: string) => `!${index.toString().padStart(3, '0')}:${label}`,
  /** Regular property snippet, optional suffix for stable ordering. */
  property: (suffix = '') => `0:${suffix}`,
  /** oneOf snippet variant – required-fields depth sorts before all-fields. */
  oneOfVariant: (depth: SnippetDepth, choiceKey: string) =>
    `${depth === 'required' ? 'z0' : 'z1'}:${choiceKey}`,
}

function snippetVariantSortKey(
  depth: SnippetDepth,
  oneOfChoices: Map<string, number>,
): string {
  const choiceKey = [...oneOfChoices.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([path, index]) => `${path}:${index}`)
    .join('|')
  return SORT_TEXT.oneOfVariant(depth, choiceKey)
}

interface SnippetVariant {
  label: string
  lines: string[]
  preview: string
  depth: SnippetDepth
  sortText: string
  description?: string
}

function buildSnippetVariants(
  schema: JsonSchema,
  root: JsonSchema,
  schemaPath: string,
  buildLines: (options: SnippetBuildOptions) => { lines: string[] },
): SnippetVariant[] {
  const sites: OneOfSite[] = []
  collectOneOfSites(schema, root, schemaPath, sites)
  const combinations = cartesianOneOfChoices(sites)
  const variants: SnippetVariant[] = []

  for (const depth of ['required', 'full'] as const) {
    for (const oneOfChoices of combinations) {
      const options: SnippetBuildOptions = { depth, oneOfChoices }
      const { lines } = buildLines(options)
      if (lines.length === 0) continue

      const preview = snippetPreviewText(lines.join('\n'))
      variants.push({
        label: snippetVariantLabel(schema, root, schemaPath, depth, oneOfChoices),
        lines,
        preview,
        depth,
        sortText: snippetVariantSortKey(depth, oneOfChoices),
        description: typeof schema.description === 'string' ? schema.description : undefined,
      })
    }
  }

  return dedupeSnippetVariants(variants)
}

function dedupeSnippetVariants(variants: SnippetVariant[]): SnippetVariant[] {
  const result: SnippetVariant[] = []
  const indexByPreview = new Map<string, number>()

  for (const variant of variants) {
    const existingIndex = indexByPreview.get(variant.preview)
    if (existingIndex === undefined) {
      indexByPreview.set(variant.preview, result.length)
      result.push(variant)
      continue
    }

    const existing = result[existingIndex]
    if (variant.depth === 'required' && existing.depth === 'full') {
      result[existingIndex] = variant
    }
  }

  return result
}

function isObjectSchema(schema: JsonSchema): boolean {
  return schema.type === 'object' || Boolean(asObject(schema.properties))
    || (schema.additionalProperties !== undefined && schema.additionalProperties !== false)
}

function isArraySchema(schema: JsonSchema): boolean {
  return schema.type === 'array' || schema.items !== undefined
}

function isNullable(schema: JsonSchema): boolean {
  if (schema.type === 'null') return true
  if (Array.isArray(schema.anyOf)) {
    return schema.anyOf.some(item => asObject(item)?.type === 'null')
  }
  return false
}

function schemaDefault(schema: JsonSchema): string | null {
  const value = schema.default
  if (value === undefined || value === null) return null
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return null
}

function schemaFirstExample(schema: JsonSchema): string | null {
  if (!Array.isArray(schema.examples) || schema.examples.length === 0) return null
  const first = schema.examples[0]
  if (first === null || first === undefined) return null
  if (typeof first === 'string') return first
  if (typeof first === 'number' || typeof first === 'boolean') return String(first)
  return null
}

function schemaFirstArrayItemExample(arraySchema: JsonSchema): string | null {
  if (!Array.isArray(arraySchema.examples) || arraySchema.examples.length === 0) return null
  for (const entry of arraySchema.examples) {
    if (typeof entry === 'string') return entry
    if (Array.isArray(entry)) {
      for (const item of entry) {
        if (typeof item === 'string') return item
      }
    }
  }
  return null
}

function schemaEnumValues(schema: JsonSchema, root: JsonSchema): string[] {
  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved || !Array.isArray(resolved.enum)) return []
  return resolved.enum.map(value => String(value))
}

function hasEnumSchema(schema: JsonSchema, root: JsonSchema): boolean {
  const branches = oneOfBranches(schema, root)
  if (branches.length > 1) {
    return branches.some(branch => schemaEnumValues(branch, root).length > 0)
  }
  return schemaEnumValues(schema, root).length > 0
}

const BOOLEAN_LITERALS = ['true', 'false'] as const

function isBooleanSchema(schema: JsonSchema, root: JsonSchema): boolean {
  const resolved = unwrapSchemaForBuild(schema, root)
  return resolved?.type === 'boolean'
}

function hasBooleanSchema(schema: JsonSchema, root: JsonSchema): boolean {
  const branches = oneOfBranches(schema, root)
  if (branches.length > 1) {
    return branches.some(branch => isBooleanSchema(branch, root))
  }
  return isBooleanSchema(schema, root)
}

function hasScalarAnyOfSchema(schema: JsonSchema, root: JsonSchema): boolean {
  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved || !Array.isArray(resolved.anyOf)) return false
  return resolved.anyOf.some(branch => {
    const item = unwrapSchemaForBuild(asObject(branch), root)
    if (!item?.type) return false
    const type = item.type
    return type === 'string' || type === 'integer' || type === 'number' || type === 'boolean'
  })
}

function hasScalarValueSuggestions(schema: JsonSchema, root: JsonSchema): boolean {
  return hasEnumSchema(schema, root)
    || hasBooleanSchema(schema, root)
    || hasScalarAnyOfSchema(schema, root)
}

function scalarSuggestionValues(schema: JsonSchema, root: JsonSchema): string[] {
  const enumValues = schemaEnumValues(schema, root)
  if (enumValues.length > 0) return enumValues
  if (hasBooleanSchema(schema, root)) return [...BOOLEAN_LITERALS]
  return []
}

function hasMatchingScalarSuggestion(
  schema: JsonSchema,
  root: JsonSchema,
  typed: string,
): boolean {
  if (!typed) return true
  return scalarSuggestionValues(schema, root).some(
    value => shouldShowEnumSuggestion(value, typed),
  )
}

function matchesEnumPrefix(value: string, prefix: string): boolean {
  if (!prefix) return true
  return value.toLowerCase().startsWith(prefix.toLowerCase())
}

function shouldShowEnumSuggestion(value: string, typedPrefix: string): boolean {
  if (!typedPrefix) return true
  if (value.toLowerCase() === typedPrefix.toLowerCase()) return false
  return matchesEnumPrefix(value, typedPrefix)
}

function propertyValueStartColumn(line: string): number | null {
  const colon = line.indexOf(':')
  if (colon < 0) return null
  let start = colon + 2
  while (start <= line.length && /\s/.test(line[start - 1] ?? '')) {
    start += 1
  }
  const leading = line[start - 1]
  if (leading === '"' || leading === "'") {
    start += 1
  }
  return start
}


function hasNonWhitespaceAfterCursor(line: string, column: number): boolean {
  return line.slice(Math.max(0, column - 1)).trim().length > 0
}

function canSuggestEnumAtPosition(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): boolean {
  const line = model.getLineContent(position.lineNumber)
  if (hasNonWhitespaceAfterCursor(line, position.column)) {
    return false
  }
  if (ctx.kind === 'property-value') {
    return true
  }
  if (ctx.kind === 'array-item') {
    return arrayItemLinePrefix(line) !== null
  }
  if (isAtArrayElementRow(model, position, ctx.objectPath)) {
    return arrayItemLinePrefix(line) !== null
  }
  return false
}

function extractTypedPropertyValue(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): string | null {
  if (ctx.kind !== 'property-value') return null
  const line = model.getLineContent(position.lineNumber)
  const start = propertyValueStartColumn(line)
  if (start === null) return null
  const raw = model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: start,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  })
  return stripYamlScalarQuotes(raw)
}

function itemSchemaOf(schema: JsonSchema): JsonSchema | null {
  const items = schema.items
  if (!items) return null
  return Array.isArray(items) ? asObject(items[0]) : asObject(items)
}


function scalarPlaceholder(
  prop: JsonSchema,
  propertyName: string,
  parentArraySchema?: JsonSchema,
): string {
  if (prop.const !== undefined) return String(prop.const)
  if (Array.isArray(prop.enum) && prop.enum.length > 0) {
    return String(prop.enum[0])
  }
  const def = schemaDefault(prop)
  if (def !== null && def !== '') return def

  const example = schemaFirstExample(prop)
    ?? (parentArraySchema ? schemaFirstArrayItemExample(parentArraySchema) : null)
  if (example !== null) return example

  const lower = propertyName.toLowerCase()
  if (lower.includes('config') || lower === 'path') return 'configs/app@latest'
  if (lower.includes('template')) return 'templates/name@latest'
  if (lower === 'schema') return 'schemas/app@latest'
  if (prop.type === 'boolean') return 'true'
  if (prop.type === 'integer' || prop.type === 'number') return '0'
  return 'value'
}

function keysForSnippet(
  objectSchema: JsonSchema,
  root: JsonSchema,
  properties: Record<string, unknown>,
  options: SnippetBuildOptions,
  schemaPath: string,
): string[] {
  if (options.depth === 'full') {
    const keys: string[] = []
    for (const [name, raw] of Object.entries(properties)) {
      const prop = resolveSchemaForBuild(
        asObject(raw),
        root,
        childSchemaPath(schemaPath, name),
        options,
      )
      if (!prop || isNullable(prop)) continue
      keys.push(name)
    }

    const minProps = typeof objectSchema.minProperties === 'number'
      ? objectSchema.minProperties
      : 0
    const additional = objectSchema.additionalProperties
    if (keys.length === 0 && minProps > 0 && additional && typeof additional === 'object') {
      keys.push('__additional__')
    }

    return keys
  }

  const required = new Set<string>(
    Array.isArray(objectSchema.required) ? objectSchema.required as string[] : [],
  )
  const keys: string[] = []

  for (const [name, raw] of Object.entries(properties)) {
    const prop = resolveSchemaForBuild(
      asObject(raw),
      root,
      childSchemaPath(schemaPath, name),
      options,
    )
    if (!prop) continue
    if (required.has(name)) {
      keys.push(name)
      continue
    }
    if (isArraySchema(prop) && typeof prop.minItems === 'number' && prop.minItems > 0) {
      keys.push(name)
    }
  }

  for (const [name, raw] of Object.entries(properties)) {
    if (keys.includes(name)) continue
    const prop = resolveSchemaForBuild(
      asObject(raw),
      root,
      childSchemaPath(schemaPath, name),
      options,
    )
    if (!prop || isNullable(prop)) continue
    const def = schemaDefault(prop)
    if (def !== null && def !== '') {
      keys.push(name)
    }
  }

  if (keys.length === 0) {
    const minProps = typeof objectSchema.minProperties === 'number'
      ? objectSchema.minProperties
      : 0
    const additional = objectSchema.additionalProperties
    if (minProps > 0 && additional && typeof additional === 'object') {
      keys.push('__additional__')
    }
  }

  return keys
}

function buildScalarFieldText(
  key: string,
  prop: JsonSchema,
  tab: number,
  placeholderOverride?: string | null,
  placeholderKind?: YamlScalarKind,
): { text: string; nextTab: number } {
  const kind = placeholderKind ?? yamlScalarKindFromSchema(prop)
  if (prop.const !== undefined) {
    return { text: `${key}: ${formatYamlScalarValue(prop.const, kind)}`, nextTab: tab }
  }
  const placeholder = placeholderOverride ?? scalarPlaceholder(prop, key)
  const formatted = formatYamlScalarSnippet(tab, placeholder, kind)
  return { text: `${key}: ${formatted.text}`, nextTab: formatted.nextTab }
}

function buildArrayItemLines(
  itemSchema: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
  startTab: number,
  options: SnippetBuildOptions = DEFAULT_SNIPPET_OPTIONS,
  schemaPath = '',
  arrayKey?: string,
  parentArraySchema?: JsonSchema,
): { lines: string[]; nextTab: number } {
  const item = resolveSchemaForBuild(itemSchema, root, schemaPath, options)
  const pad = indent(indentLevel)

  if (!item) {
    return { lines: [`${pad}- `], nextTab: startTab }
  }

  if (isObjectSchema(item)) {
    const properties = asObject(item.properties) ?? {}
    const keys = keysForSnippet(item, root, properties, options, schemaPath)

    if (keys.length === 0) {
      return { lines: [`${pad}- `], nextTab: startTab }
    }

    const lines: string[] = []
    let tab = startTab
    const firstKey = keys[0]

    if (firstKey === '__additional__') {
      const addSchema = resolveSchemaForBuild(
        asObject(item.additionalProperties),
        root,
        childSchemaPath(schemaPath, '__additional__'),
        options,
      )
      const placeholder = addSchema ? scalarPlaceholder(addSchema, 'key') : 'value'
      const formatted = formatYamlScalarSnippet(tab, placeholder, yamlScalarKindFromSchema(addSchema))
      lines.push(`${pad}- key: ${formatted.text}`)
      return { lines, nextTab: formatted.nextTab }
    }

    const firstProp = resolveSchemaForBuild(
      asObject(properties[firstKey]),
      root,
      childSchemaPath(schemaPath, firstKey),
      options,
    )
    if (!firstProp) {
      return { lines: [`${pad}- `], nextTab: startTab }
    }

    if (isObjectSchema(firstProp) || isArraySchema(firstProp)) {
      lines.push(`${pad}- ${firstKey}:`)
      const nested = isArraySchema(firstProp)
        ? buildArrayPropertyLines(
          firstKey,
          firstProp,
          root,
          indentLevel + 1,
          tab,
          options,
          childSchemaPath(schemaPath, firstKey),
        )
        : buildObjectLines(
          firstProp,
          root,
          indentLevel + 1,
          tab,
          options,
          childSchemaPath(schemaPath, firstKey),
        )
      lines.push(...nested.lines)
      tab = nested.nextTab
    } else {
      const firstField = buildScalarFieldText(firstKey, firstProp, tab)
      lines.push(`${pad}- ${firstField.text}`)
      tab = firstField.nextTab
    }

    for (const key of keys.slice(1)) {
      const prop = resolveSchemaForBuild(
        asObject(properties[key]),
        root,
        childSchemaPath(schemaPath, key),
        options,
      )
      if (!prop) continue
      const fieldLines = buildPropertyLines(
        key,
        prop,
        root,
        indentLevel + 1,
        tab,
        options,
        childSchemaPath(schemaPath, key),
      )
      lines.push(...fieldLines.lines)
      tab = fieldLines.nextTab
    }

    return { lines, nextTab: tab }
  }

  const placeholder = scalarPlaceholder(item, arrayKey ?? 'item', parentArraySchema)
  const formatted = formatYamlScalarSnippet(startTab, placeholder, yamlScalarKindFromSchema(item))
  return {
    lines: [`${pad}- ${formatted.text}`],
    nextTab: formatted.nextTab,
  }
}

function buildArrayPropertyLines(
  key: string,
  prop: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
  startTab: number,
  options: SnippetBuildOptions = DEFAULT_SNIPPET_OPTIONS,
  schemaPath = '',
): { lines: string[]; nextTab: number } {
  const itemSchema = itemSchemaOf(prop) ?? {}
  const count = arrayItemCount(prop)
  const lines: string[] = []
  let tab = startTab
  const itemsPath = childSchemaPath(schemaPath, 'items')

  lines.push(`${key}:`)

  for (let i = 0; i < count; i++) {
    const itemLines = buildArrayItemLines(
      itemSchema,
      root,
      indentLevel,
      tab,
      options,
      itemsPath,
      key,
      prop,
    )
    lines.push(...itemLines.lines)
    tab = itemLines.nextTab
  }

  return { lines, nextTab: tab }
}

function buildPropertyLines(
  key: string,
  propSchema: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
  startTab: number,
  options: SnippetBuildOptions = DEFAULT_SNIPPET_OPTIONS,
  schemaPath = '',
  mapContext?: { mapSchema: JsonSchema; mapKey: string },
): { lines: string[]; nextTab: number } {
  const prop = resolveSchemaForBuild(propSchema, root, schemaPath, options)
  const pad = indent(indentLevel)
  if (!prop) {
    return { lines: [`${pad}${key}: `], nextTab: startTab }
  }

  if (key === '__additional__') {
    const addSchema = resolveSchemaForBuild(
      asObject(prop.additionalProperties),
      root,
      childSchemaPath(schemaPath, '__additional__'),
      options,
    ) ?? prop
    const placeholder = scalarPlaceholder(addSchema, 'key')
    const formatted = formatYamlScalarSnippet(startTab, placeholder, yamlScalarKindFromSchema(addSchema))
    return {
      lines: [`${pad}key: ${formatted.text}`],
      nextTab: formatted.nextTab,
    }
  }

  if (isObjectSchema(prop)) {
    const lines = [`${pad}${key}:`]
    const nested = buildObjectLines(prop, root, indentLevel + 1, startTab, options, schemaPath)
    lines.push(...nested.lines)
    return { lines, nextTab: nested.nextTab }
  }

  if (isArraySchema(prop)) {
    const arrayLines = buildArrayPropertyLines(
      key,
      prop,
      root,
      indentLevel + 1,
      startTab,
      options,
      schemaPath,
    )
    return {
      lines: arrayLines.lines.map((line, index) => (index === 0 ? `${pad}${line}` : line)),
      nextTab: arrayLines.nextTab,
    }
  }

  const mapExample = mapContext
    ? schemaMapEntryFieldExample(mapContext.mapSchema, mapContext.mapKey, key)
    : null
  const scalar = buildScalarFieldText(
    key,
    prop,
    startTab,
    mapExample?.value ?? null,
    mapExample?.kind,
  )
  return {
    lines: [`${pad}${scalar.text}`],
    nextTab: scalar.nextTab,
  }
}

function buildObjectLines(
  schema: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
  startTab: number,
  options: SnippetBuildOptions = DEFAULT_SNIPPET_OPTIONS,
  schemaPath = '',
): { lines: string[]; nextTab: number } {
  const resolved = resolveSchemaForBuild(schema, root, schemaPath, options)
  if (!resolved || !isObjectSchema(resolved)) {
    return { lines: [], nextTab: startTab }
  }

  const properties = asObject(resolved.properties) ?? {}
  const keys = keysForSnippet(resolved, root, properties, options, schemaPath)
  const lines: string[] = []
  let tab = startTab

  for (const key of keys) {
    const raw = key === '__additional__'
      ? resolved.additionalProperties
      : properties[key]
    let prop = resolveSchemaForBuild(
      asObject(raw),
      root,
      childSchemaPath(schemaPath, key),
      options,
    )
    if (!prop && key !== '__additional__') continue

    if (key === 'options' && schemaPath.endsWith('.cast')) {
      const format = castFormatDefault(resolved, root)
      const specific = resolveCastOptionsSchema(root, format)
      if (specific) prop = specific
    }

    const fieldLines = buildPropertyLines(
      key,
      key === '__additional__' ? resolved : prop ?? {},
      root,
      indentLevel,
      tab,
      options,
      childSchemaPath(schemaPath, key === '__additional__' ? '__additional__' : key),
    )
    lines.push(...fieldLines.lines)
    tab = fieldLines.nextTab
  }

  if (lines.length === 0) {
    const mapValue = mapValueSchema(resolved, root)
    if (mapValue && isObjectSchema(mapValue)) {
      const mapKey = schemaFirstMapKey(resolved) ?? 'param_name'
      const fieldLines = buildPropertyLines(
        mapKey,
        mapValue,
        root,
        indentLevel,
        tab,
        options,
        childSchemaPath(schemaPath, mapKey),
        { mapSchema: resolved, mapKey },
      )
      lines.push(...fieldLines.lines)
      tab = fieldLines.nextTab
    } else {
      const scalarMapValue = mapScalarValueSchema(resolved, root)
      if (scalarMapValue) {
        const examples = schemaMapExampleEntries(resolved)
        if (examples.length > 0) {
          for (const entry of examples) {
            const field = buildScalarFieldText(
              entry.key,
              scalarMapValue,
              tab,
              entry.value,
              entry.kind,
            )
            lines.push(`${indent(indentLevel)}${field.text}`)
            tab = field.nextTab
          }
        } else {
          const mapKey = schemaFirstMapKey(resolved) ?? 'param_name'
          const field = buildScalarFieldText(mapKey, scalarMapValue, tab)
          lines.push(`${indent(indentLevel)}${field.text}`)
          tab = field.nextTab
        }
      }
    }
  }

  return { lines, nextTab: tab }
}

function buildPropertyInsertText(
  name: string,
  propSchema: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
  options: SnippetBuildOptions = DEFAULT_SNIPPET_OPTIONS,
  schemaPath = '',
): { insertText: string; isSnippet: boolean; preview: string } {
  const prop = resolveSchemaForBuild(propSchema, root, schemaPath, options)
  if (!prop) {
    const plain = `${name}: `
    return { insertText: plain, isSnippet: false, preview: plain }
  }

  if (isObjectSchema(prop)) {
    const body = buildObjectLines(
      prop,
      root,
      indentLevel + 1,
      1,
      options,
      childSchemaPath(schemaPath, name),
    )
    if (body.lines.length === 0) {
      const plain = `${name}:\n${indent(indentLevel + 1)}`
      return { insertText: plain, isSnippet: false, preview: plain }
    }
    const insertText = `${name}:\n${body.lines.join('\n')}`
    return {
      insertText,
      isSnippet: true,
      preview: snippetPreviewText(insertText),
    }
  }

  if (isArraySchema(prop)) {
    const arrayLines = buildArrayPropertyLines(
      name,
      prop,
      root,
      indentLevel + 1,
      1,
      options,
      childSchemaPath(schemaPath, name),
    )
    const insertText = arrayLines.lines.join('\n')
    return {
      insertText,
      isSnippet: true,
      preview: snippetPreviewText(insertText),
    }
  }

  const scalar = buildScalarFieldText(name, prop, 1)
  return {
    insertText: scalar.text,
    isSnippet: true,
    preview: snippetPreviewText(scalar.text),
  }
}

function buildArrayItemInsertText(
  itemSchema: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
  options: SnippetBuildOptions = DEFAULT_SNIPPET_OPTIONS,
): { insertText: string; preview: string } {
  const body = buildArrayItemLines(itemSchema, root, indentLevel, 1, options)
  const insertText = body.lines
    .map((line, index) => (index === 0 ? line.replace(/^\s*-\s*/, '') : line))
    .join('\n')
  return {
    insertText,
    preview: snippetPreviewText(body.lines.join('\n')),
  }
}

function snippetPreviewText(insertText: string): string {
  return insertText
    .replace(/\$\{\d+:([^}]*)\}/g, '$1')
    .replace(/\$\d+/g, '')
}

function schemaDescription(schema: JsonSchema | null | undefined): string | undefined {
  if (!schema) return undefined
  if (typeof schema.description === 'string' && schema.description.trim()) {
    return schema.description.trim()
  }
  return undefined
}

function completionDocumentation(
  description: string | undefined,
): { value: string; isTrusted?: boolean } | undefined {
  if (!description) return undefined
  return { value: description, isTrusted: true }
}

function previewSummary(preview: string): string {
  const firstLine = preview.split('\n')[0] ?? preview
  if (preview.includes('\n')) {
    return `${firstLine} …`
  }
  return firstLine
}

/** Secondary suggest-widget text that must not repeat the primary label prefix. */
function formatCompletionPreviewDetail(primaryLabel: string, preview: string): string {
  const summary = previewSummary(preview)
  const baseLabel = primaryLabel.replace(/\s*\([^)]*\)\s*$/, '').trim()
  const keyPrefix = `${baseLabel}:`

  if (summary === keyPrefix || summary === `${keyPrefix} …`) {
    return preview.includes('\n') ? '…' : 'snippet'
  }

  if (summary.startsWith(keyPrefix)) {
    const rest = summary.slice(keyPrefix.length).trimStart()
    if (!rest || rest === '…') {
      return preview.includes('\n') ? '…' : 'snippet'
    }
    return rest
  }

  return summary
}

function schemaAtPath(
  root: JsonSchema,
  path: string[],
  options: SchemaPathOptions = {},
): JsonSchema | null {
  const enterBefore = new Set(options.enterArrayItemBefore ?? [])
  let current: JsonSchema | null = root

  for (let i = 0; i < path.length; i++) {
    if (enterBefore.has(i)) {
      current = unwrapSchema(current, root)
      if (!current || !isArraySchema(current)) return null
      const items = itemSchemaOf(current)
      current = items ? resolveRef(items, root) : null
      if (!current) return null
    }

    current = unwrapSchema(current, root)
    if (!current) return null
    const segment = path[i]

    // Direct property match
    const properties = asObject(current.properties)
    if (properties && segment in properties) {
      current = asObject(properties[segment])
      continue
    }
    const additional = current.additionalProperties
    if (additional && typeof additional === 'object') {
      current = asObject(additional)
      continue
    }

    // oneOf-aware fallback: current may be { oneOf: [...] } without direct properties.
    // Walk each branch and take the first that declares the segment.
    const branches = oneOfBranches(current, root)
    if (branches.length > 0) {
      let found: JsonSchema | null = null
      for (const branch of branches) {
        const bProps = asObject(branch.properties)
        if (bProps && segment in bProps) {
          found = asObject(bProps[segment])
          break
        }
        const bAdditional = branch.additionalProperties
        if (bAdditional && typeof bAdditional === 'object') {
          found = asObject(bAdditional)
          break
        }
      }
      if (found) {
        current = found
        continue
      }
    }

    return null
  }

  current = unwrapSchema(current, root)
  if (!current) return null

  if (options.enterArrayItemAtEnd && isArraySchema(current)) {
    const items = itemSchemaOf(current)
    return items ? resolveRef(items, root) : null
  }

  return current
}

function schemaPathOptions(
  ctx: YamlCompletionContext,
  enterAtEnd = false,
): SchemaPathOptions {
  return {
    enterArrayItemBefore: ctx.arrayItemEnterBefore,
    enterArrayItemAtEnd: enterAtEnd,
  }
}

function findEnclosingArrayItemIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  rowIndent?: number,
): number | null {
  const lineIndent = rowIndent ?? propertyRowIndent(model, lineNumber)
  const currentLine = model.getLineContent(lineNumber)
  let best: number | null = null

  if (isArrayItemLine(currentLine)) {
    const itemIndent = currentLine.search(/\S/)
    if (itemIndent >= 0) {
      best = itemIndent
    }
  }

  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    if (!isArrayItemLine(line)) continue
    const itemIndent = line.search(/\S/)
    if (itemIndent < lineIndent && (best === null || itemIndent > best)) {
      best = itemIndent
    }
  }

  return best
}

function yamlFieldValuesInArrayItemScope(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
): Record<string, string> {
  const values: Record<string, string> = {}
  const arrayItemIndent = findEnclosingArrayItemIndent(model, lineNumber)
  if (arrayItemIndent === null) {
    return values
  }

  for (let ln = lineNumber; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const currentIndent = line.search(/\S/)
    if (currentIndent < arrayItemIndent) break
    if (currentIndent === arrayItemIndent && isArrayItemLine(line) && ln < lineNumber) {
      break
    }

    const key = lineArrayItemKey(line) ?? lineKey(line)
    if (!key) continue
    const colon = line.indexOf(':')
    if (colon < 0) continue
    const rawValue = line.slice(colon + 1).trim()
    if (!rawValue) continue
    values[key] = rawValue.replace(/^["']|["']$/g, '')
  }

  return values
}

function branchMatchesConstDiscriminators(
  branch: JsonSchema,
  values: Record<string, string>,
): boolean {
  const props = asObject(branch.properties) ?? {}
  let hasConst = false
  for (const [key, raw] of Object.entries(props)) {
    const prop = asObject(raw)
    if (prop?.const === undefined) continue
    hasConst = true
    if (values[key] !== String(prop.const)) return false
  }
  return hasConst
}

function resolveOneOfBranch(
  schema: JsonSchema,
  root: JsonSchema,
  values: Record<string, string>,
): JsonSchema | null {
  const branches = oneOfBranches(schema, root)
  if (branches.length === 0) {
    return unwrapSchema(schema, root)
  }
  if (branches.length === 1) {
    return branches[0]
  }
  for (const branch of branches) {
    if (branchMatchesConstDiscriminators(branch, values)) {
      return branch
    }
  }
  return null
}

function resolveOneOfPropertySchema(
  oneOfParent: JsonSchema,
  root: JsonSchema,
  propertyKey: string,
  resolvedBranch: JsonSchema | null,
): JsonSchema | null {
  if (resolvedBranch) return null

  const branches = oneOfBranches(oneOfParent, root)
  if (branches.length <= 1) return null

  const propSchemas: JsonSchema[] = []
  for (const branch of branches) {
    const props = asObject(branch.properties)
    const prop = props?.[propertyKey] ? asObject(props[propertyKey]) : null
    if (prop) {
      const resolved = unwrapSchema(prop, root)
      if (resolved) propSchemas.push(resolved)
    }
  }
  if (propSchemas.length === 0) return null

  const enumValues: string[] = []
  for (const prop of propSchemas) {
    if (prop.const !== undefined) enumValues.push(String(prop.const))
    if (Array.isArray(prop.enum)) {
      enumValues.push(...prop.enum.map(value => String(value)))
    }
  }
  if (enumValues.length > 0) {
    const unique = [...new Set(enumValues)]
    const description = propSchemas.find(prop => typeof prop.description === 'string')?.description
    return description ? { enum: unique, description } : { enum: unique }
  }
  if (propSchemas.length === 1) return propSchemas[0]
  return { anyOf: propSchemas }
}

function resolveArrayItemSchema(
  itemsSchema: JsonSchema,
  root: JsonSchema,
  model: Monaco.editor.ITextModel,
  lineNumber: number,
): JsonSchema | null {
  const resolved = resolveRef(itemsSchema, root)
  const values = yamlFieldValuesInArrayItemScope(model, lineNumber)
  const branch = resolveOneOfBranch(resolved, root, values)
  if (branch) return branch
  if (oneOfBranches(resolved, root).length > 1) {
    return resolved
  }
  return unwrapSchema(resolved, root)
}

function resolveTargetSchema(
  root: JsonSchema,
  ctx: YamlCompletionContext,
  model?: Monaco.editor.ITextModel,
  lineNumber?: number,
  column?: number,
): JsonSchema | null {
  if (ctx.kind === 'array-item') {
    const arraySchema = schemaAtPath(root, ctx.objectPath, schemaPathOptions(ctx))
    if (!arraySchema || !isArraySchema(arraySchema)) return null
    const items = itemSchemaOf(arraySchema)
    if (!items) return null
    if (model && lineNumber) {
      return resolveArrayItemSchema(items, root, model, lineNumber)
    }
    return unwrapSchema(resolveRef(items, root), root)
  }

  if (ctx.kind === 'property-value' && ctx.valuePropertyKey) {
    let base = schemaAtPath(
      root,
      ctx.objectPath,
      schemaPathOptions(ctx, ctx.insideArrayItem),
    )
    if (model && lineNumber && isCastOptionsObjectPath(ctx.objectPath)) {
      const castOptions = resolveCastOptionsFromContext(root, model, lineNumber, ctx.objectPath)
      if (castOptions) base = castOptions
    }
    if (!base) return null
    const oneOfParent = oneOfBranches(base, root).length > 1 ? base : null
    let resolvedOneOfBranch: JsonSchema | null = null
    if (model && lineNumber) {
      const inArrayObject = ctx.insideArrayItem
        || (column !== undefined && isWithinArrayItemObject(model, lineNumber, column))
      if (inArrayObject) {
        const branch = resolveOneOfBranch(
          base,
          root,
          yamlFieldValuesInArrayItemScope(model, lineNumber),
        )
        if (branch) {
          resolvedOneOfBranch = branch
          base = branch
        }
      }
    }
    const properties = asObject(base.properties)
    let propSchema: JsonSchema | null = null
    if (properties && ctx.valuePropertyKey in properties) {
      propSchema = asObject(properties[ctx.valuePropertyKey])
    } else {
      const additional = base.additionalProperties
      if (additional && typeof additional === 'object') {
        propSchema = asObject(additional)
      }
    }
    if (oneOfParent) {
      const mergedProperty = resolveOneOfPropertySchema(
        oneOfParent,
        root,
        ctx.valuePropertyKey,
        null,
      )
      if (mergedProperty) {
        if (Array.isArray(mergedProperty.enum)) {
          propSchema = mergedProperty
        } else if (!propSchema && !resolvedOneOfBranch) {
          propSchema = mergedProperty
        }
      }
    } else if (!propSchema) {
      propSchema = resolveOneOfPropertySchema(
        base,
        root,
        ctx.valuePropertyKey,
        resolvedOneOfBranch,
      )
    }
    if (!propSchema) return null
    return unwrapSchema(propSchema, root)
  }

  const inArrayItemObject = ctx.insideArrayItem
    || Boolean(
      model && lineNumber && column !== undefined
      && isWithinArrayItemObject(model, lineNumber, column),
    )

  if (inArrayItemObject && model && lineNumber) {
    const parentSchema = schemaAtPath(root, ctx.objectPath, schemaPathOptions(ctx))
    if (parentSchema && isArraySchema(parentSchema)) {
      const items = itemSchemaOf(parentSchema)
      if (items) {
        const branch = resolveArrayItemSchema(items, root, model, lineNumber)
        if (branch) return branch
      }
    }
  }

  const enterArrayItem = inArrayItemObject

  if (model && lineNumber && isCastOptionsObjectPath(ctx.objectPath)) {
    const castOptions = resolveCastOptionsFromContext(root, model, lineNumber, ctx.objectPath)
    if (castOptions) return castOptions
  }

  return schemaAtPath(
    root,
    ctx.objectPath,
    schemaPathOptions(ctx, enterArrayItem),
  )
}


/**
 * Innermost `- key:` array item that encloses the current property row.
 */
function enclosingArrayItemKeyLineIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  rowIndent?: number,
): number | null {
  return findEnclosingArrayItemIndent(model, lineNumber, rowIndent)
}

function inferredPropertyRowIndent(model: Monaco.editor.ITextModel, lineNumber: number): number {
  let prevLine: string | null = null
  let prevIndent = -1
  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const content = model.getLineContent(ln)
    const trimmed = content.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    prevLine = content
    prevIndent = content.search(/\S/)
    break
  }

  if (prevLine && lineKey(prevLine) && /:\s*$/.test(prevLine)) {
    return prevIndent + 2
  }

  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const content = model.getLineContent(ln)
    const trimmed = content.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const lineIndent = content.search(/\S/)

    if (isArrayItemLine(content) && !lineArrayItemKey(content)) {
      continue
    }

    const key = lineKey(content)
    if (key) {
      return lineIndent
    }

    if (isArrayItemLine(content) && lineArrayItemKey(content)) {
      return lineIndent + 2
    }
  }

  return 0
}

/**
 * Indent column for the cursor on the current line.
 * Uses whitespace before the cursor when the line has no content there yet.
 */
function effectivePropertyRowIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  column: number,
): number {
  const line = model.getLineContent(lineNumber)
  const beforeCursor = line.slice(0, Math.max(0, column - 1))
  if (beforeCursor.search(/\S/) >= 0) {
    return line.search(/\S/)
  }
  if (beforeCursor.length > 0) {
    return beforeCursor.length
  }
  if (line.trim().length === 0) {
    return inferredPropertyRowIndent(model, lineNumber)
  }
  if (column <= 1) {
    return 0
  }
  return inferredPropertyRowIndent(model, lineNumber)
}

/**
 * Indent column for a property key row at the cursor (legacy: end of line).
 */
function propertyRowIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  column?: number,
): number {
  if (column !== undefined) {
    return effectivePropertyRowIndent(model, lineNumber, column)
  }
  const line = model.getLineContent(lineNumber)
  const explicit = line.search(/\S/)
  if (explicit >= 0) return explicit
  return inferredPropertyRowIndent(model, lineNumber)
}

function expectedPropertyRowIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  objectPath: string[],
  insideArrayItem: boolean,
  column?: number,
): number | null {
  if (objectPath.length === 0) {
    return 0
  }
  if (insideArrayItem) {
    const rowIndent = column !== undefined
      ? effectivePropertyRowIndent(model, lineNumber, column)
      : propertyRowIndent(model, lineNumber)
    const itemIndent = enclosingArrayItemKeyLineIndent(model, lineNumber, rowIndent)
    if (itemIndent !== null) return itemIndent + 2
    const arrayIndent = arrayKeyLineIndent(model, lineNumber, objectPath)
    if (arrayIndent >= 0) return arrayIndent + 4
    return null
  }
  const parentKey = objectPath[objectPath.length - 1]
  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    if (lineKey(line) === parentKey) {
      return line.search(/\S/) + 2
    }
  }
  return null
}

function expectedArrayElementRowIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  objectPath: string[],
): number | null {
  const arrayKeyIndent = arrayKeyLineIndent(model, lineNumber, objectPath)
  if (arrayKeyIndent < 0) return null
  return arrayKeyIndent + 2
}

function isAtPropertyRow(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): boolean {
  const effective = effectivePropertyRowIndent(model, position.lineNumber, position.column)
  const expected = expectedPropertyRowIndent(
    model,
    position.lineNumber,
    ctx.objectPath,
    ctx.insideArrayItem,
    position.column,
  )
  return expected !== null && effective === expected
}

function isAtArrayElementRow(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  objectPath: string[],
): boolean {
  const line = model.getLineContent(position.lineNumber)
  if (isScalarArrayItemLine(line)) {
    return true
  }
  if (/^\s*-\s*\S/.test(line) && lineArrayItemKey(line)) {
    return false
  }
  const effective = effectivePropertyRowIndent(model, position.lineNumber, position.column)
  const expected = expectedArrayElementRowIndent(model, position.lineNumber, objectPath)
  return expected !== null && effective === expected
}

function isWithinArrayItemObject(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  column: number,
): boolean {
  const rowIndent = effectivePropertyRowIndent(model, lineNumber, column)
  const arrayItemIndent = enclosingArrayItemKeyLineIndent(model, lineNumber, rowIndent)
  if (arrayItemIndent === null) return false
  return rowIndent > arrayItemIndent
}

function arrayKeyLineIndent(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  objectPath: string[],
): number {
  if (!objectPath.length) return -1
  const arrayKey = objectPath[objectPath.length - 1]
  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    if (lineKey(line) === arrayKey) {
      return line.search(/\S/)
    }
  }
  return -1
}

function isArrayElementRow(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  lineContent: string,
  objectPath: string[],
  column: number,
): boolean {
  if (/^\s*-\s/.test(lineContent)) return true
  const expected = expectedArrayElementRowIndent(model, lineNumber, objectPath)
  if (expected === null) return false
  const effective = effectivePropertyRowIndent(model, lineNumber, column)
  return effective === expected
}

function parentYamlContext(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  column: number,
): {
  objectPath: string[]
  insideArrayItem: boolean
  arrayItemEnterBefore: number[]
} {
  const currentLine = model.getLineContent(lineNumber)
  const currentIndent = effectivePropertyRowIndent(model, lineNumber, column)

  const keyFrames: { key: string; indent: number }[] = []
  const arrayItemIndents: number[] = []
  let insideArrayItem = isArrayItemLine(currentLine)
  let seekIndent = currentIndent

  if (isArrayItemLine(currentLine)) {
    const lineIndent = currentLine.search(/\S/)
    if (lineIndent >= 0) arrayItemIndents.push(lineIndent)
  }

  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const lineIndent = line.search(/\S/)
    if (lineIndent >= seekIndent) continue

    if (isArrayItemLine(line)) {
      insideArrayItem = true
      arrayItemIndents.push(lineIndent)
      seekIndent = lineIndent
      continue
    }

    const key = lineKey(line)
    if (key) {
      keyFrames.unshift({ key, indent: lineIndent })
      seekIndent = lineIndent
      if (lineIndent === 0) break
    }
  }

  const objectPath = keyFrames.map(frame => frame.key)
  const arrayItemEnterBefore: number[] = []
  for (let i = 1; i < keyFrames.length; i++) {
    const low = keyFrames[i - 1].indent
    const high = keyFrames[i].indent
    if (arrayItemIndents.some(ai => ai > low && ai < high)) {
      arrayItemEnterBefore.push(i)
    }
  }

  if (!insideArrayItem && isWithinArrayItemObject(model, lineNumber, column)) {
    insideArrayItem = true
  }

  return { objectPath, insideArrayItem, arrayItemEnterBefore }
}

function currentLineIndent(model: Monaco.editor.ITextModel, lineNumber: number): number {
  return propertyRowIndent(model, lineNumber)
}

function existingKeysInScope(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  column: number,
  insideArrayItem: boolean,
): Set<string> {
  const lineIndent = effectivePropertyRowIndent(model, lineNumber, column)
  const keys = new Set<string>()
  const scopedInsideArrayItem = insideArrayItem
    || isWithinArrayItemObject(model, lineNumber, column)

  if (!scopedInsideArrayItem) {
    for (let ln = 1; ln <= model.getLineCount(); ln++) {
      const line = model.getLineContent(ln)
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#')) continue
      if (line.search(/\S/) !== lineIndent) continue
      const key = lineKey(line)
      if (key) keys.add(key)
    }
    return keys
  }

  for (let ln = lineNumber; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const currentIndent = line.search(/\S/)
    if (currentIndent < lineIndent) {
      if (isArrayItemLine(line)) {
        const itemKey = lineArrayItemKey(line)
        if (itemKey) keys.add(itemKey)
        break
      }
      if (lineKey(line)) break
    }
    if (currentIndent === lineIndent) {
      const key = lineKey(line) ?? lineArrayItemKey(line)
      if (key) keys.add(key)
    }
  }

  for (let ln = lineNumber + 1; ln <= model.getLineCount(); ln++) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const currentIndent = line.search(/\S/)
    if (currentIndent < lineIndent) {
      if (isArrayItemLine(line) || lineKey(line)) break
    }
    if (currentIndent === lineIndent) {
      const key = lineKey(line) ?? lineArrayItemKey(line)
      if (key) keys.add(key)
    }
  }

  return keys
}

function completionContext(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): YamlCompletionContext {
  const line = model.getLineContent(position.lineNumber)
  const colonIdx = line.indexOf(':')
  const { objectPath, insideArrayItem: parentInsideArray, arrayItemEnterBefore } = parentYamlContext(
    model,
    position.lineNumber,
    position.column,
  )
  const propertyRowSpaces = effectivePropertyRowIndent(model, position.lineNumber, position.column)
  const indentLevel = Math.floor(propertyRowSpaces / 2)
  const insideArrayItem = parentInsideArray
    || isWithinArrayItemObject(model, position.lineNumber, position.column)

  const baseContext = { objectPath, arrayItemEnterBefore, indentLevel, propertyRowSpaces, insideArrayItem }

  if (/^\s*-\s*/.test(line)) {
    const afterDashStart = line.search(/-/) + 1
    const afterDash = line.slice(afterDashStart).replace(/^\s*/, '')
    const itemKey = lineArrayItemKey(line)
    const localColon = afterDash.indexOf(':')

    if (itemKey && localColon >= 0) {
      const valueStartColumn = afterDashStart + afterDash.slice(0, localColon + 1).length + 1
      if (position.column >= valueStartColumn) {
        return {
          ...baseContext,
          kind: 'property-value',
          valuePropertyKey: itemKey,
        }
      }
      return {
        ...baseContext,
        kind: 'property-key',
      }
    }

    return {
      ...baseContext,
      kind: 'array-item',
    }
  }

  const key = lineKey(line)
  if (colonIdx >= 0 && position.column > colonIdx + 1 && key) {
    return {
      ...baseContext,
      kind: 'property-value',
      valuePropertyKey: key,
    }
  }

  if (key && colonIdx >= 0 && position.column <= colonIdx + 1) {
    return {
      ...baseContext,
      kind: 'property-key',
    }
  }

  return {
    ...baseContext,
    kind: 'property-key',
  }
}

function leadingIndentPrefix(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  column: number,
): string {
  const rowSpaces = effectivePropertyRowIndent(model, lineNumber, column)
  const beforeCursor = model.getLineContent(lineNumber).slice(0, Math.max(0, column - 1))
  const existingLeading = beforeCursor.length - beforeCursor.trimStart().length
  return ' '.repeat(Math.max(0, rowSpaces - existingLeading))
}

/**
 * Format a multi-line property snippet for Monaco InsertAsSnippet.
 * Continuation-line leading spaces are relative to the property row (rowSpaces),
 * which matches how VS Code / Monaco preserve nested structure on insert.
 */
function formatPropertyInsertForSnippet(insertText: string, rowSpaces: number): string {
  const lines = insertText.split('\n')
  if (lines.length <= 1) return lines[0]?.trimStart() ?? ''

  const head = lines[0].trimStart()
  const body = lines.slice(1).map(line => {
    const relative = Math.max(0, bodyLineLeadingSpaces(line) - rowSpaces)
    return ' '.repeat(relative) + line.trimStart()
  })
  return [head, ...body].join('\n')
}

function finalizePropertyInsertText(
  built: { insertText: string; isSnippet: boolean },
  indentPrefix: string,
  rowSpaces: number,
): { insertText: string; isSnippet: boolean } {
  if (!built.insertText.includes('\n')) {
    const insertText = built.isSnippet
      ? escapeMonacoSnippetDollars(indentPrefix + built.insertText)
      : indentPrefix + built.insertText
    return { insertText, isSnippet: built.isSnippet }
  }
  const formatted = formatPropertyInsertForSnippet(built.insertText, rowSpaces)
  const lines = formatted.split('\n')
  lines[0] = indentPrefix + lines[0]
  return {
    insertText: escapeMonacoSnippetDollars(lines.join('\n')),
    isSnippet: true,
  }
}

function extractTypedScalarArrayItem(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): string | null {
  const line = model.getLineContent(position.lineNumber)
  const dashPrefix = arrayItemLinePrefix(line)
  if (!dashPrefix) return null
  const raw = model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: dashPrefix.dashEndColumn,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  })
  return stripYamlScalarQuotes(raw)
}

function schemaMapEntryFieldExample(
  mapSchema: JsonSchema,
  mapKey: string,
  fieldKey: string,
): { value: string; kind: YamlScalarKind } | null {
  if (!Array.isArray(mapSchema.examples)) return null
  for (const entry of mapSchema.examples) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) continue
    const param = asObject((entry as Record<string, unknown>)[mapKey])
    if (!param) continue
    const value = param[fieldKey]
    if (typeof value === 'string') return { value, kind: 'string' }
    if (typeof value === 'boolean') {
      return { value: value ? 'true' : 'false', kind: 'boolean' }
    }
    if (typeof value === 'number') {
      return {
        value: String(value),
        kind: Number.isInteger(value) ? 'integer' : 'number',
      }
    }
  }
  return null
}
function schemaFirstMapKey(schema: JsonSchema): string | null {
  if (!Array.isArray(schema.examples) || schema.examples.length === 0) return null
  const first = schema.examples[0]
  if (first && typeof first === 'object' && !Array.isArray(first)) {
    const keys = Object.keys(first as Record<string, unknown>)
    return keys[0] ?? null
  }
  return null
}

interface ScalarMapExampleEntry {
  key: string
  value: string
  kind: YamlScalarKind
}

function yamlScalarKindFromValue(value: unknown): YamlScalarKind {
  if (typeof value === 'boolean') return 'boolean'
  if (typeof value === 'number') return Number.isInteger(value) ? 'integer' : 'number'
  return 'string'
}

function schemaMapExampleEntries(mapSchema: JsonSchema): ScalarMapExampleEntry[] {
  if (!Array.isArray(mapSchema.examples)) return []
  for (const example of mapSchema.examples) {
    if (!example || typeof example !== 'object' || Array.isArray(example)) continue
    const entries: ScalarMapExampleEntry[] = []
    for (const [key, value] of Object.entries(example as Record<string, unknown>)) {
      if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        entries.push({
          key,
          value: typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value),
          kind: yamlScalarKindFromValue(value),
        })
      }
    }
    if (entries.length > 0) return entries
  }
  return []
}

function isCastOptionsObjectPath(objectPath: string[]): boolean {
  return objectPath.length >= 2
    && objectPath[objectPath.length - 1] === 'options'
    && objectPath[objectPath.length - 2] === 'cast'
}

function castFormatDefault(castSchema: JsonSchema, root: JsonSchema): string {
  const resolved = unwrapSchemaForBuild(castSchema, root)
  const formatProp = asObject(asObject(resolved?.properties)?.format)
  const formatResolved = formatProp ? unwrapSchemaForBuild(formatProp, root) : null
  if (!formatResolved) return 'yaml'
  const def = schemaDefault(formatResolved)
  if (def !== null) return def
  if (Array.isArray(formatResolved.enum) && formatResolved.enum.length > 0) {
    return String(formatResolved.enum[0])
  }
  return 'yaml'
}

function resolveCastOptionsSchema(root: JsonSchema, format: string): JsonSchema | null {
  const defs = asObject(root.$defs)
  if (!defs) return null

  const cast = asObject(defs.CastSchema)
  const allOf = Array.isArray(cast?.allOf) ? cast.allOf : []
  for (const clause of allOf) {
    const condition = asObject(clause)
    const ifProps = asObject(asObject(condition?.if)?.properties)
    const formatSchema = asObject(ifProps?.format)
    if (formatSchema?.const !== format) continue
    const thenProps = asObject(asObject(condition?.then)?.properties)
    const optionsRef = asObject(thenProps?.options)
    const ref = optionsRef?.$ref
    if (typeof ref !== 'string' || !ref.startsWith('#/$defs/')) continue
    const defName = ref.slice('#/$defs/'.length)
    return asObject(defs[defName])
  }

  const fallback: Record<string, string> = {
    yaml: 'YamlCastOptionsSchema',
    json: 'JsonCastOptionsSchema',
    env: 'EnvCastOptionsSchema',
    hcl: 'HclCastOptionsSchema',
    raw: 'RawCastOptionsSchema',
  }
  const defName = fallback[format]
  return defName ? asObject(defs[defName]) : null
}

function yamlObjectFieldValue(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  objectPath: string[],
  fieldKey: string,
): string | null {
  if (!objectPath.length) return null

  const parentKey = objectPath[objectPath.length - 1]
  let objectIndent: number | null = null
  for (let ln = lineNumber; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    if (lineKey(line) === parentKey) {
      objectIndent = line.search(/\S/)
      break
    }
  }
  if (objectIndent === null) return null

  const fieldIndent = objectIndent + 2
  for (let ln = lineNumber; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const lineIndent = line.search(/\S/)
    if (lineIndent < objectIndent) break
    if (lineIndent !== fieldIndent) continue
    if (lineKey(line) !== fieldKey) continue
    const colon = line.indexOf(':')
    if (colon < 0) continue
    return stripYamlScalarQuotes(line.slice(colon + 1).trim())
  }
  return null
}

function resolveCastOptionsFromContext(
  root: JsonSchema,
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  objectPath: string[],
): JsonSchema | null {
  if (!isCastOptionsObjectPath(objectPath)) return null
  const castPath = objectPath.slice(0, -1)
  const castSchema = schemaAtPath(root, castPath)
  const format = yamlObjectFieldValue(model, lineNumber, castPath, 'format')
    ?? (castSchema ? castFormatDefault(castSchema, root) : 'yaml')
  return resolveCastOptionsSchema(root, format)
}

function mapValueSchema(schema: JsonSchema, root: JsonSchema): JsonSchema | null {
  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved) return null
  const properties = asObject(resolved.properties)
  if (properties && Object.keys(properties).length > 0) return null
  const additional = resolved.additionalProperties
  if (additional && typeof additional === 'object') {
    const addSchema = unwrapSchemaForBuild(asObject(additional), root)
    if (addSchema && isObjectSchema(addSchema) && asObject(addSchema.properties)) {
      return addSchema
    }
  }
  return null
}

function mapScalarValueSchema(schema: JsonSchema, root: JsonSchema): JsonSchema | null {
  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved) return null
  const properties = asObject(resolved.properties)
  if (properties && Object.keys(properties).length > 0) return null
  const additional = resolved.additionalProperties
  if (!additional || typeof additional !== 'object') return null
  const addSchema = unwrapSchemaForBuild(asObject(additional), root)
  if (!addSchema) return null
  if (isObjectSchema(addSchema) && asObject(addSchema.properties)) return null
  return addSchema
}

function buildScalarMapEntrySuggestion(
  monaco: typeof Monaco,
  mapKey: string,
  valueSchema: JsonSchema,
  range: Monaco.IRange,
  indentPrefix: string,
  rowSpaces: number,
  placeholderOverride?: ScalarMapExampleEntry | null,
  mapDescription?: string,
): Monaco.languages.CompletionItem {
  const kind = placeholderOverride?.kind ?? yamlScalarKindFromSchema(valueSchema)
  const placeholder = placeholderOverride?.value
    ?? scalarPlaceholder(valueSchema, mapKey)
  const formatted = formatYamlScalarSnippet(1, placeholder, kind)
  const insertText = `${mapKey}: ${formatted.text}`
  const finalized = finalizePropertyInsertText(
    { insertText, isSnippet: formatted.nextTab > 1 },
    indentPrefix,
    rowSpaces,
  )
  return {
    label: mapKey,
    kind: monaco.languages.CompletionItemKind.Snippet,
    insertText: finalized.insertText,
    insertTextRules: finalized.isSnippet
      ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
      : undefined,
    range,
    filterText: mapKey,
    detail: 'parameter',
    sortText: SORT_TEXT.property(mapKey),
    documentation: completionDocumentation(mapDescription ?? schemaDescription(valueSchema)),
  }
}

interface PropertyVariant {
  label: string
  description?: string
  insertText: string
  isSnippet: boolean
  preview: string
  sortText: string
}

function propertySuggestionsForObject(
  monaco: typeof Monaco,
  schema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  indentLevel: number,
  existingKeys: Set<string>,
  branchLabel?: string,
  indentPrefix = '',
  rowSpaces = 0,
): Monaco.languages.CompletionItem[] {
  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved) return []

  const properties = asObject(resolved.properties) ?? {}
  const fixedEntries = Object.entries(properties)
    .filter(([name]) => !existingKeys.has(name))

  if (fixedEntries.length > 0) {
    return fixedEntries.flatMap(([name, propSchema]) => {
      const prop = asObject(propSchema) ?? {}
      const propResolved = unwrapSchemaForBuild(prop, root)
      const fieldDescription = schemaDescription(propResolved)
      const snippetDepth: SnippetDepth = propResolved
        && (isObjectSchema(propResolved) || isArraySchema(propResolved))
        ? 'full'
        : 'required'
      const buildOptions: SnippetBuildOptions = {
        ...DEFAULT_SNIPPET_OPTIONS,
        depth: snippetDepth,
      }

      const variants: PropertyVariant[] = hasOneOf(prop, root)
        ? propertySnippetVariants(name, prop, root, indentLevel)
        : (() => {
          const built = buildPropertyInsertText(name, prop, root, indentLevel, buildOptions)
          return [{
            label: name,
            insertText: built.insertText,
            isSnippet: built.isSnippet,
            preview: built.preview,
            sortText: SORT_TEXT.property(),
          }]
        })()
      return variants.map(variant => {
        const label = branchLabel && variants.length === 1 && !hasOneOf(prop, root)
          ? `${name} (${branchLabel})`
          : variant.label
        const finalized = finalizePropertyInsertText(
          { insertText: variant.insertText, isSnippet: variant.isSnippet },
          indentPrefix,
          rowSpaces,
        )
        return {
          label,
          kind: monaco.languages.CompletionItemKind.Snippet,
          insertText: finalized.insertText,
          insertTextRules: finalized.isSnippet
            ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
            : undefined,
          range,
          filterText: name,
          detail: variant.isSnippet
            ? formatCompletionPreviewDetail(name, variant.preview)
            : (typeof prop.type === 'string' ? prop.type : undefined),
          documentation: completionDocumentation(variant.description ?? fieldDescription),
          sortText: variant.sortText,
        }
      })
    })
  }

  const valueSchema = mapValueSchema(resolved, root)
  if (valueSchema && isObjectSchema(valueSchema)) {
    const built = buildPropertyInsertText(
      'param_name',
      valueSchema,
      root,
      indentLevel,
      { ...DEFAULT_SNIPPET_OPTIONS, depth: 'required' },
    )
    const lines = built.insertText.split('\n')
    const head = (lines[0] ?? '').replace(/^param_name:/, '${1:name}:')
    const body = lines.slice(1).map(line => line.replace(
      /\$\{(\d+)(:[^}]*)?\}/g,
      (_match, index: string, label = '') => `\${${Number(index) + 1}${label}}`,
    ))
    const insertText = [head, ...body].join('\n')
    const finalized = finalizePropertyInsertText(
      { insertText, isSnippet: built.isSnippet },
      indentPrefix,
      rowSpaces,
    )
    return [{
      label: { label: 'name', detail: 'new map entry' },
      kind: monaco.languages.CompletionItemKind.Snippet,
      insertText: finalized.insertText,
      insertTextRules: finalized.isSnippet
        ? monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
        : undefined,
      range,
      filterText: 'name',
      detail: 'parameter',
      documentation: completionDocumentation(schemaDescription(resolved)),
      sortText: SORT_TEXT.property('name'),
    }]
  }

  const scalarMapValue = mapScalarValueSchema(resolved, root)
  if (scalarMapValue) {
    const examples = schemaMapExampleEntries(resolved)
      .filter(entry => !existingKeys.has(entry.key))
    if (examples.length > 0) {
      return examples.map(entry => buildScalarMapEntrySuggestion(
        monaco,
        entry.key,
        scalarMapValue,
        range,
        indentPrefix,
        rowSpaces,
        entry,
        schemaDescription(resolved),
      ))
    }
    return [buildScalarMapEntrySuggestion(
      monaco,
      'param_name',
      scalarMapValue,
      range,
      indentPrefix,
      rowSpaces,
      null,
      schemaDescription(resolved),
    )]
  }

  return []
}

function propertySnippetVariants(
  name: string,
  propSchema: JsonSchema,
  root: JsonSchema,
  indentLevel: number,
): PropertyVariant[] {
  const resolved = resolveRef(propSchema, root)
  const variants = buildSnippetVariants(
    resolved,
    root,
    '',
    options => {
      const result = buildPropertyInsertText(name, resolved, root, indentLevel, options, '')
      return { lines: result.insertText.split('\n') }
    },
  )

  if (variants.length === 0) {
    const { insertText, isSnippet, preview } = buildPropertyInsertText(
      name,
      propSchema,
      root,
      indentLevel,
    )
    return [{
      label: name,
      insertText,
      isSnippet,
      preview,
      sortText: SORT_TEXT.property(),
    }]
  }

  return variants.map(variant => {
    const insertText = variant.lines.join('\n')
    return {
      label: `${name} (${variant.label})`,
      description: variant.description,
      insertText,
      isSnippet: true,
      preview: variant.preview,
      sortText: variant.sortText,
    }
  })
}

function propertySuggestions(
  monaco: typeof Monaco,
  schema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  indentLevel: number,
  existingKeys: Set<string>,
  indentPrefix = '',
  rowSpaces = 0,
): Monaco.languages.CompletionItem[] {
  const objectBranches = oneOfBranches(schema, root)
  if (objectBranches.length > 1) {
    return objectBranches.flatMap((branch, index) => {
      if (!isObjectSchema(branch)) return []
      return propertySuggestionsForObject(
        monaco,
        branch,
        root,
        range,
        indentLevel,
        existingKeys,
        oneOfVariantLabel(branch, index),
        indentPrefix,
        rowSpaces,
      )
    })
  }

  return propertySuggestionsForObject(
    monaco,
    schema,
    root,
    range,
    indentLevel,
    existingKeys,
    undefined,
    indentPrefix,
    rowSpaces,
  )
}


function shouldOfferArrayItemObjectSnippets(itemSchema: JsonSchema, root: JsonSchema): boolean {
  const branches = oneOfBranches(itemSchema, root)
  if (branches.length > 1) {
    return branches.some(branch => isObjectSchema(branch))
  }
  const resolved = unwrapSchema(resolveRef(itemSchema, root), root)
  return resolved ? isObjectSchema(resolved) : false
}

function oneOfConstDiscriminatorSuggestions(
  monaco: typeof Monaco,
  itemSchema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  lineContent: string,
): Monaco.languages.CompletionItem[] | null {
  if (!isEmptyScalarArrayItemLine(lineContent)) return null

  const branches = oneOfBranches(itemSchema, root)
  if (branches.length < 2) return null

  let discriminatorKey: string | null = null
  const values: string[] = []

  for (const branch of branches) {
    const props = asObject(branch.properties) ?? {}
    let branchKey: string | null = null
    let branchValue: string | null = null
    for (const [key, raw] of Object.entries(props)) {
      const prop = asObject(raw)
      if (prop?.const === undefined) continue
      branchKey = key
      branchValue = String(prop.const)
      break
    }
    if (!branchKey || !branchValue) return null
    if (discriminatorKey === null) discriminatorKey = branchKey
    else if (discriminatorKey !== branchKey) return null
    values.push(branchValue)
  }

  if (!discriminatorKey || values.length < 2) return null

  return values.map((value, index) => ({
    label: { label: `${discriminatorKey}: ${value}`, description: discriminatorKey },
    kind: monaco.languages.CompletionItemKind.EnumMember,
    insertText: `${discriminatorKey}: ${value}`,
    range,
    filterText: `${discriminatorKey} ${value}`,
    sortText: SORT_TEXT.enumValue(index, value),
    detail: discriminatorKey,
    documentation: `${discriminatorKey}: ${value}`,
  }))
}


function arrayItemIndentFromContext(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  lineContent: string,
  objectPath: string[],
): number {
  const dashMatch = lineContent.match(/^(\s*)-/)
  if (dashMatch) {
    return Math.floor(dashMatch[1].length / 2)
  }

  if (objectPath.length > 0) {
    const arrayKey = objectPath[objectPath.length - 1]
    for (let ln = lineNumber - 1; ln >= 1; ln--) {
      const line = model.getLineContent(ln)
      if (lineKey(line) === arrayKey) {
        const keyIndent = line.search(/\S/)
        if (keyIndent >= 0) {
          return Math.floor(keyIndent / 2) + 1
        }
      }
    }
  }

  return Math.floor(currentLineIndent(model, lineNumber) / 2)
}

/**
 * Monaco re-indents multi-line snippet bodies relative to the current line.
 * Continuation lines use indentation relative to anchorSpaces (current row indent).
 */
function formatNestedSnippetInsert(lines: string[], anchorSpaces: number): string {
  if (lines.length === 0) return ''
  const head = lines[0].trimStart()
  if (lines.length === 1) return head

  const toRelative = (line: string): string => {
    const relative = Math.max(0, bodyLineLeadingSpaces(line) - anchorSpaces)
    return ' '.repeat(relative) + line.trimStart()
  }

  return [head, ...lines.slice(1).map(toRelative)].join('\n')
}

function formatArrayItemInsertText(bodyLines: string[], lineContent: string): string {
  if (bodyLines.length === 0) return ''

  const anchorSpaces = bodyLineLeadingSpaces(bodyLines[0])
  const formatted = formatNestedSnippetInsert(bodyLines, anchorSpaces)
  const hasDashOnLine = /^\s*-/.test(lineContent)
  if (!hasDashOnLine) return formatted

  const dashSuffixMatch = lineContent.match(/^(\s*-\s*)(.*)$/)
  const firstContent = bodyLines[0].replace(/^\s*-\s*/, '')
  const needsLeadingSpace = dashSuffixMatch?.[1].endsWith('-') ?? false
  const head = needsLeadingSpace && firstContent ? ` ${firstContent}` : firstContent
  const continuation = formatted.split('\n').slice(1)
  return [head, ...continuation].join('\n')
}

function arrayItemSuggestions(
  monaco: typeof Monaco,
  itemSchema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  ctx: YamlCompletionContext,
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  lineContent: string,
): Monaco.languages.CompletionItem[] {
  const resolved = resolveRef(itemSchema, root)
  const effectiveIndent = arrayItemIndentFromContext(
    model,
    lineNumber,
    lineContent,
    ctx.objectPath,
  )

  const variants = buildSnippetVariants(
    resolved,
    root,
    '',
    options => buildArrayItemLines(resolved, root, effectiveIndent, 1, options, ''),
  )

  return variants.map(variant => {
    const insertText = formatArrayItemInsertText(variant.lines, lineContent)
    return {
      label: variant.label,
      kind: monaco.languages.CompletionItemKind.Snippet,
      insertText,
      insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
      range,
      detail: formatCompletionPreviewDetail(variant.label, variant.preview),
      documentation: completionDocumentation(variant.description),
      sortText: variant.sortText,
    }
  })
}

function valueSuggestions(
  monaco: typeof Monaco,
  schema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  typedPrefix = '',
): Monaco.languages.CompletionItem[] {
  const branches = oneOfBranches(schema, root)
  if (branches.length > 1) {
    const suggestions: Monaco.languages.CompletionItem[] = []
    const seen = new Set<string>()
    for (const [index, branch] of branches.entries()) {
      const suffix = oneOfVariantLabel(branch, index)
      for (const item of valueSuggestionsForBranch(monaco, branch, root, range, typedPrefix)) {
        const dedupeKey = `${item.insertText}`
        if (seen.has(dedupeKey)) continue
        seen.add(dedupeKey)
        suggestions.push({
          ...item,
          label: `${item.label} (${suffix})`,
          detail: 'oneOf',
        })
      }
    }
    return suggestions
  }

  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved) return []
  return valueSuggestionsForBranch(monaco, resolved, root, range, typedPrefix)
}

function valueSuggestionsForBranch(
  monaco: typeof Monaco,
  schema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  typedPrefix = '',
): Monaco.languages.CompletionItem[] {
  const resolved = unwrapSchemaForBuild(schema, root)
  if (!resolved) return []

  if (Array.isArray(resolved.anyOf) && !Array.isArray(resolved.enum)) {
    const merged: Monaco.languages.CompletionItem[] = []
    const seen = new Set<string>()
    for (const branch of resolved.anyOf) {
      const item = asObject(branch)
      if (!item) continue
      for (const suggestion of valueSuggestionsForBranch(monaco, item, root, range, typedPrefix)) {
        const key = String(suggestion.insertText)
        if (seen.has(key)) continue
        seen.add(key)
        merged.push(suggestion)
      }
    }
    if (merged.length > 0) return merged
  }

  const scalarKind = yamlScalarKindFromSchema(resolved)
  const valueDocumentation = completionDocumentation(schemaDescription(resolved))
  const suggestions: Monaco.languages.CompletionItem[] = []

  if (Array.isArray(resolved.enum)) {
    resolved.enum.forEach((value, index) => {
      const label = String(value)
      if (!shouldShowEnumSuggestion(label, typedPrefix)) return
      const insertText = formatYamlScalarValue(value, scalarKind)
      suggestions.push({
        label,
        kind: monaco.languages.CompletionItemKind.EnumMember,
        insertText,
        range,
        filterText: label,
        sortText: SORT_TEXT.enumValue(index, label),
        documentation: valueDocumentation,
      })
    })
  }

  if (resolved.const !== undefined) {
    const label = String(resolved.const)
    if (shouldShowEnumSuggestion(label, typedPrefix)) {
      suggestions.push({
        label,
        kind: monaco.languages.CompletionItemKind.Value,
        insertText: formatYamlScalarValue(resolved.const, scalarKind),
        range,
        filterText: label,
        sortText: SORT_TEXT.enumValue(0, label),
        documentation: valueDocumentation,
      })
    }
  }

  if (resolved.type === 'boolean') {
    for (const value of BOOLEAN_LITERALS) {
      if (!shouldShowEnumSuggestion(value, typedPrefix)) continue
      suggestions.push({
        label: value,
        kind: monaco.languages.CompletionItemKind.Value,
        insertText: value,
        range,
        filterText: value,
        documentation: valueDocumentation,
      })
    }
  }

  return suggestions
}

function completionRange(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): Monaco.IRange {
  if (ctx.kind === 'array-item') {
    const line = model.getLineContent(position.lineNumber)
    const dashPrefix = arrayItemLinePrefix(line)
    if (dashPrefix) {
      return {
        startLineNumber: position.lineNumber,
        startColumn: dashPrefix.dashEndColumn,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      }
    }
  }

  const line = model.getLineContent(position.lineNumber)
  if (ctx.kind === 'property-value') {
    const valueStart = propertyValueStartColumn(line)
    if (valueStart !== null) {
      return {
        startLineNumber: position.lineNumber,
        startColumn: valueStart,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      }
    }
  }

  const word = model.getWordUntilPosition(position)
  if (word.word) {
    return {
      startLineNumber: position.lineNumber,
      startColumn: word.startColumn,
      endLineNumber: position.lineNumber,
      endColumn: word.endColumn,
    }
  }

  if (ctx.kind === 'property-key') {
    const leadingSpaces = line.match(/^(\s*)/)?.[1].length ?? 0
    if (leadingSpaces > 0 && position.column > leadingSpaces) {
      return {
        startLineNumber: position.lineNumber,
        startColumn: leadingSpaces + 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      }
    }
  }

  return {
    startLineNumber: position.lineNumber,
    startColumn: position.column,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  }
}

function editorHasSelection(editor: Monaco.editor.ICodeEditor): boolean {
  const selection = editor.getSelection()
  return selection !== null && !selection.isEmpty()
}

function abortSignalFromToken(token?: Monaco.CancellationToken): AbortSignal | undefined {
  if (!token) return undefined
  const controller = new AbortController()
  if (token.isCancellationRequested) {
    controller.abort()
    return controller.signal
  }
  const subscription = token.onCancellationRequested(() => {
    controller.abort()
    subscription.dispose()
  })
  return controller.signal
}

function scalarArrayItemValueSuggestions(
  monaco: typeof Monaco,
  itemSchema: JsonSchema,
  root: JsonSchema,
  range: Monaco.IRange,
  ctx: YamlCompletionContext,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  lineContent: string,
): Monaco.languages.CompletionItem[] | null {
  if (!hasScalarValueSuggestions(itemSchema, root)) return null
  if (!arrayItemLinePrefix(lineContent)) {
    if (!shouldOfferArrayItemObjectSnippets(itemSchema, root)) {
      return []
    }
    return arrayItemSuggestions(
      monaco,
      itemSchema,
      root,
      range,
      ctx,
      model,
      position.lineNumber,
      lineContent,
    )
  }
  if (!canSuggestEnumAtPosition(model, position, ctx)) {
    return []
  }
  const typed = extractTypedScalarArrayItem(model, position) ?? ''
  return valueSuggestions(monaco, itemSchema, root, range, typed).map(item => ({
    ...item,
    insertText: formatScalarArrayItemInsertText(lineContent, String(item.insertText ?? '')),
  }))
}

export type { ParameterCompletionOptions } from './ocmoParameterCompletion'

interface PositionAnalysis {
  ctx: YamlCompletionContext
  targetSchema: JsonSchema | null
  lineContent: string
  range: Monaco.IRange
  indentPrefix: string
}

interface PositionAnalysisCache {
  versionId: number
  line: number
  column: number
  rootSchema: JsonSchema
  result: PositionAnalysis
}

let _positionAnalysisCache: PositionAnalysisCache | null = null

/**
 * Computes (and caches for one keystroke) the context, target schema, line content, completion
 * range, and indent prefix for the given position. The cache is keyed on model version, line,
 * column, and root schema identity, so it is safe to call from shouldAutoTrigger, hasCompletion,
 * and buildCompletionSuggestions within the same Monaco keystroke event.
 */
function analyzePosition(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  rootSchema: JsonSchema,
): PositionAnalysis {
  const versionId = model.getVersionId()
  if (
    _positionAnalysisCache
    && _positionAnalysisCache.versionId === versionId
    && _positionAnalysisCache.line === position.lineNumber
    && _positionAnalysisCache.column === position.column
    && _positionAnalysisCache.rootSchema === rootSchema
  ) {
    return _positionAnalysisCache.result
  }
  const ctx = completionContext(model, position)
  const targetSchema = resolveTargetSchema(rootSchema, ctx, model, position.lineNumber, position.column)
  const lineContent = model.getLineContent(position.lineNumber)
  const range = completionRange(model, position, ctx)
  const indentPrefix = leadingIndentPrefix(model, position.lineNumber, position.column)
  const result: PositionAnalysis = { ctx, targetSchema, lineContent, range, indentPrefix }
  _positionAnalysisCache = { versionId, line: position.lineNumber, column: position.column, rootSchema, result }
  return result
}

/** Discriminator → scalar → object-snippet pipeline shared by both array-element paths. */
function syncArrayElementSuggestions(
  monaco: typeof Monaco,
  itemSchema: JsonSchema,
  rootSchema: JsonSchema,
  range: Monaco.IRange,
  ctx: ReturnType<typeof completionContext>,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  lineContent: string,
): Monaco.languages.CompletionItem[] {
  const discriminator = oneOfConstDiscriminatorSuggestions(
    monaco,
    itemSchema,
    rootSchema,
    range,
    lineContent,
  )
  if (discriminator?.length) return discriminator
  if (hasScalarValueSuggestions(itemSchema, rootSchema)) {
    const scalars = scalarArrayItemValueSuggestions(
      monaco,
      itemSchema,
      rootSchema,
      range,
      ctx,
      model,
      position,
      lineContent,
    )
    if (scalars !== null) return scalars
  }
  if (!shouldOfferArrayItemObjectSnippets(itemSchema, rootSchema)) return []
  return arrayItemSuggestions(
    monaco,
    itemSchema,
    rootSchema,
    range,
    ctx,
    model,
    position.lineNumber,
    lineContent,
  )
}

function buildYamlCompletionSuggestions(
  monaco: typeof Monaco,
  rootSchema: JsonSchema,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  uriOptions?: UriReferenceCompletionOptions | null,
  paramOptions?: ParameterCompletionOptions | null,
  token?: Monaco.CancellationToken,
): Monaco.languages.CompletionItem[] | Promise<Monaco.languages.CompletionItem[]> {
  const { ctx, targetSchema, lineContent, range, indentPrefix } = analyzePosition(model, position, rootSchema)
  const beforeCursor = lineContent.slice(0, Math.max(0, position.column - 1))

  if (paramOptions) {
    const paramSuggestions = buildParameterPlaceholderSuggestions(
      monaco,
      model,
      position,
      ctx,
      paramOptions,
    )
    if (paramSuggestions.length > 0) {
      return paramSuggestions
    }
  }

  const metadataKey = paramOptions?.metadataKey ?? ctx.objectPath[0] ?? null
  const declaration = detectOcmoParameterDeclarationContext(
    model,
    position,
    ctx,
    metadataKey,
  )
  if (
    declaration
    && ctx.kind === 'property-key'
    && isAtParameterFieldRow(model, position, declaration)
  ) {
    const parameterSchema = resolveParameterDeclarationSchema(rootSchema, declaration.objectPath)
    if (parameterSchema) {
      const existingKeys = existingKeysInYamlObject(
        model,
        declaration.objectPath,
        position.lineNumber,
      )
      return propertySuggestions(
        monaco,
        parameterSchema,
        rootSchema,
        range,
        ctx.indentLevel,
        existingKeys,
        indentPrefix,
        ctx.propertyRowSpaces,
      )
    }
  }

  if (!targetSchema) return []

  if (/^\s+$/.test(beforeCursor)) {
    const atPropertyRow = isAtPropertyRow(model, position, ctx)
    const atArrayRow = isAtArrayElementRow(model, position, ctx.objectPath)
    if (!atPropertyRow && !atArrayRow) {
      return []
    }
  }

  if (ctx.kind === 'property-value') {
    if (metadataKey ?? declaration?.objectPath[0]) {
      const valueDeclaration = detectOcmoParameterValueContext(
        model,
        position,
        ctx,
        metadataKey ?? declaration?.objectPath[0],
      )
      if (valueDeclaration) {
        const parameterType = readOcmoParameterType(
          model,
          valueDeclaration.objectPath[0],
          valueDeclaration.parameterName,
        )
        if (parameterType === 'dynamic') {
          return []
        }
        if (parameterType === 'projected') {
          return buildParameterProjectedValueSuggestions(monaco, model, position)
        }
        if (parameterType === 'secret' && uriOptions) {
          return buildSecretPathSuggestions(
            monaco,
            ctx,
            model,
            position,
            uriOptions,
            abortSignalFromToken(token),
          )
        }
      }
    }

    const signal = abortSignalFromToken(token)
    const uriPromise = uriOptions
      ? buildUriReferenceSuggestions(
        monaco,
        targetSchema,
        rootSchema,
        ctx,
        model,
        position,
        uriOptions,
        signal,
      )
      : Promise.resolve([])
    return uriPromise.then(uriSuggestions => {
      const typedPrefix = extractTypedPropertyValue(model, position, ctx) ?? ''
      const staticSuggestions = uriSuggestions.length > 0
        ? []
        : canSuggestEnumAtPosition(model, position, ctx)
          ? valueSuggestions(monaco, targetSchema, rootSchema, range, typedPrefix)
          : []
      return [...uriSuggestions, ...staticSuggestions]
    })
  }

  if (ctx.kind === 'array-item') {
    if (/^\s+$/.test(beforeCursor) && !isAtArrayElementRow(model, position, ctx.objectPath)) {
      return []
    }
    const scalarUriReference = hasUriReferenceFormat(targetSchema, rootSchema)
      && uriOptions
      && (isInOcmoMetadata(ctx.objectPath, uriOptions.metadataKey)
        || uriOptions.allowOutsideMetadata)
    if (scalarUriReference) {
      const typed = extractTypedUriReference(model, position, ctx)
      const canBrowseEmpty = uriOptions.allowOutsideMetadata
        && (typed === null || typed.pathPart === '')
      if (typed?.pathPart || canBrowseEmpty) {
        return buildUriReferenceSuggestions(
          monaco,
          targetSchema,
          rootSchema,
          ctx,
          model,
          position,
          uriOptions!,
          abortSignalFromToken(token),
        ).then(uriSuggestions => {
          if (uriSuggestions.length > 0) return uriSuggestions
          return syncArrayElementSuggestions(
            monaco, targetSchema, rootSchema, range, ctx, model, position, lineContent,
          )
        })
      }
    }
    return syncArrayElementSuggestions(
      monaco, targetSchema, rootSchema, range, ctx, model, position, lineContent,
    )
  }

  const onPropertyKeyLine = lineKey(lineContent) !== null && !/^\s*-/.test(lineContent.trim())
  if (
    !onPropertyKeyLine
    && isAtArrayElementRow(model, position, ctx.objectPath)
  ) {
    const arrayParent = schemaAtPath(
      rootSchema,
      ctx.objectPath,
      schemaPathOptions(ctx),
    )
    if (arrayParent && isArraySchema(arrayParent)) {
      const items = itemSchemaOf(arrayParent)
      if (items) {
        const itemSchema = resolveRef(items, rootSchema)
        if (!itemSchema) return []
        const arrayRange = completionRange(model, position, { ...ctx, kind: 'array-item' })
        return syncArrayElementSuggestions(
          monaco,
          itemSchema,
          rootSchema,
          arrayRange,
          { ...ctx, kind: 'array-item' },
          model,
          position,
          lineContent,
        )
      }
    }
  }

  const existingKeys = existingKeysInScope(
    model,
    position.lineNumber,
    position.column,
    ctx.insideArrayItem,
  )

  if (
    isJsonSchemaDocumentSchema(rootSchema)
    && ctx.kind === 'property-key'
    && isJsonSchemaDocumentRootContext(ctx, metadataKey ?? '_ocmo', lineContent, position.column)
    && shouldOfferJsonSchemaRootSnippet(model)
  ) {
    return [buildJsonSchemaRootSnippetSuggestion(monaco, range, indentPrefix)]
  }

  const effectiveTargetSchema = resolveJsonSchemaTargetSchema(
    rootSchema,
    targetSchema,
    ctx,
    model,
    position,
  )

  if (!canSuggestInParameterDeclarationObject(model, position, ctx.objectPath, metadataKey)) {
    return []
  }

  return propertySuggestions(
    monaco,
    effectiveTargetSchema,
    rootSchema,
    range,
    ctx.indentLevel,
    existingKeys,
    indentPrefix,
    ctx.propertyRowSpaces,
  )
}

function hasYamlCompletionSuggestions(
  monaco: typeof Monaco,
  rootSchema: JsonSchema | null,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  uriOptions?: UriReferenceCompletionOptions | null,
  paramOptions?: ParameterCompletionOptions | null,
): boolean {
  if (!rootSchema) return false
  const { ctx, targetSchema } = analyzePosition(model, position, rootSchema)
  if (paramOptions && shouldSuggestParameterPlaceholders(model, position, ctx, paramOptions)) {
    return true
  }
  const metadataKey = paramOptions?.metadataKey ?? ctx.objectPath[0] ?? null
  if (shouldSuggestParameterDeclarationFields(model, position, ctx, metadataKey, rootSchema)) {
    return true
  }
  if (metadataKey && shouldSuggestParameterValue(model, position, ctx, metadataKey)) {
    return true
  }
  if (
    uriOptions
    && targetSchema
    && shouldSuggestUriReferences(
      targetSchema,
      rootSchema,
      ctx,
      uriOptions,
      extractTypedUriReference(model, position, ctx),
    )
  ) {
    return true
  }
  if (
    targetSchema
    && (ctx.kind === 'property-value' || ctx.kind === 'array-item')
    && hasScalarValueSuggestions(targetSchema, rootSchema)
  ) {
    if (!canSuggestEnumAtPosition(model, position, ctx)) {
      return false
    }
    const typed = ctx.kind === 'property-value'
      ? extractTypedPropertyValue(model, position, ctx) ?? ''
      : extractTypedScalarArrayItem(model, position) ?? ''
    return hasMatchingScalarSuggestion(targetSchema, rootSchema, typed)
  }
  if (ctx.kind === 'property-key' && targetSchema && isAtPropertyRow(model, position, ctx)) {
    if (!canSuggestInParameterDeclarationObject(model, position, ctx.objectPath, metadataKey)) {
      return false
    }
    const existingKeys = existingKeysInScope(
      model,
      position.lineNumber,
      position.column,
      ctx.insideArrayItem,
    )
    const properties = asObject(unwrapSchema(targetSchema, rootSchema)?.properties)
    if (properties && Object.keys(properties).some(key => !existingKeys.has(key))) {
      return true
    }
  }
  const suggestions = buildYamlCompletionSuggestions(
    monaco,
    rootSchema,
    model,
    position,
    uriOptions,
    paramOptions,
  )
  return Array.isArray(suggestions) ? suggestions.length > 0 : true
}

function hasScalarTrigger(
  targetSchema: JsonSchema,
  rootSchema: JsonSchema,
  ctx: YamlCompletionContext,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): boolean {
  return !!(
    hasScalarValueSuggestions(targetSchema, rootSchema)
    && canSuggestEnumAtPosition(model, position, ctx)
  )
}

export function shouldAutoTriggerYamlSuggest(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  uriOptions?: UriReferenceCompletionOptions | null,
  rootSchema?: JsonSchema | null,
  paramOptions?: ParameterCompletionOptions | null,
): boolean {
  const line = model.getLineContent(position.lineNumber)
  const before = line.slice(0, Math.max(0, position.column - 1))
  // When the cursor is mid-word (not after a colon), check only inline triggers.
  if (before.trim().length > 0 && !/:\s*$/.test(before)) {
    const ctx = rootSchema
      ? analyzePosition(model, position, rootSchema).ctx
      : completionContext(model, position)
    if (paramOptions && shouldSuggestParameterPlaceholders(model, position, ctx, paramOptions)) {
      return true
    }
    const metadataKey = paramOptions?.metadataKey ?? ctx.objectPath[0] ?? null
    if (metadataKey && shouldSuggestParameterValue(model, position, ctx, metadataKey)) {
      return true
    }
    if (rootSchema && (ctx.kind === 'property-value' || ctx.kind === 'array-item')) {
      const targetSchema = analyzePosition(model, position, rootSchema).targetSchema
      if (targetSchema) {
        if (
          uriOptions
          && shouldSuggestUriReferences(
            targetSchema,
            rootSchema,
            ctx,
            uriOptions,
            extractTypedUriReference(model, position, ctx),
          )
        ) {
          return true
        }
        if (hasScalarTrigger(targetSchema, rootSchema, ctx, model, position)) return true
      }
    }
    if (ctx.kind === 'property-value') return false
  }
  // After a colon or at line start: use memoized analysis when possible.
  const analysis = rootSchema ? analyzePosition(model, position, rootSchema) : null
  const ctx = analysis?.ctx ?? completionContext(model, position)
  const metadataKey = paramOptions?.metadataKey ?? ctx.objectPath[0] ?? null
  if (shouldSuggestParameterDeclarationFields(model, position, ctx, metadataKey, rootSchema ?? null)) {
    return true
  }
  if (metadataKey && shouldSuggestParameterValue(model, position, ctx, metadataKey)) {
    return true
  }
  if (ctx.kind === 'property-value') {
    if (!rootSchema || !analysis?.targetSchema) return false
    return hasScalarTrigger(analysis.targetSchema, rootSchema, ctx, model, position)
  }
  if (ctx.kind === 'array-item') {
    if (rootSchema && analysis?.targetSchema) {
      if (hasScalarTrigger(analysis.targetSchema, rootSchema, ctx, model, position)) return true
    }
    return isAtArrayElementRow(model, position, ctx.objectPath)
  }
  if (isAtArrayElementRow(model, position, ctx.objectPath)) {
    return true
  }
  if (shouldSuggestParameterDeclarationFields(model, position, ctx, metadataKey, rootSchema ?? null)) {
    return true
  }
  if (!canSuggestInParameterDeclarationObject(model, position, ctx.objectPath, metadataKey)) {
    return false
  }
  return isAtPropertyRow(model, position, ctx)
}

function hideSuggestWidget(editor: Monaco.editor.IStandaloneCodeEditor): void {
  const controller = editor.getContribution('editor.contrib.suggestController') as {
    cancelSuggestWidget?: () => void
  } | null
  controller?.cancelSuggestWidget?.()
}

function preferSuggestBelowWhenNeeded(
  editor: Monaco.editor.IStandaloneCodeEditor,
  monaco: typeof import('monaco-editor'),
): void {
  const position = editor.getPosition()
  if (!position) return

  const visible = editor.getScrolledVisiblePosition(position)
  if (!visible) return

  const lineHeight = editor.getOption(monaco.editor.EditorOption.lineHeight)
  const minSpaceAbove = lineHeight * 6
  if (visible.top >= minSpaceAbove) return

  const widget = editor.getContribution('editor.contrib.suggestWidget') as {
    stopForceRenderingAbove?: () => void
  } | null
  widget?.stopForceRenderingAbove?.()
}

export function installYamlCompletionTriggers(
  editor: Monaco.editor.IStandaloneCodeEditor,
  monaco: typeof Monaco,
  getSchema: () => JsonSchema | null,
  getUriReference?: () => UriReferenceCompletionOptions | null,
  getParameterCompletion?: () => ParameterCompletionOptions | null,
): Monaco.IDisposable {
  let timer: ReturnType<typeof setTimeout> | null = null

  const schedule = () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      const model = editor.getModel()
      const position = editor.getPosition()
      if (!model || !position || model.getLanguageId() !== 'yaml') return
      if (editorHasSelection(editor)) {
        hideSuggestWidget(editor)
        return
      }
      const rootSchema = getSchema()
      const paramOptions = getParameterCompletion?.() ?? null
      if (!shouldAutoTriggerYamlSuggest(
        model,
        position,
        getUriReference?.() ?? null,
        rootSchema,
        paramOptions,
      )) {
        hideSuggestWidget(editor)
        return
      }
      if (!hasYamlCompletionSuggestions(
        monaco,
        rootSchema,
        model,
        position,
        getUriReference?.() ?? null,
        paramOptions,
      )) {
        hideSuggestWidget(editor)
        return
      }
      preferSuggestBelowWhenNeeded(editor, monaco)
      editor.trigger('yaml', 'editor.action.triggerSuggest', { auto: true })
    }, 80)
  }

  const cursorDisposable = editor.onDidChangeCursorPosition(e => {
    if (e.source === 'mouse') return
    schedule()
  })
  const selectionDisposable = editor.onDidChangeCursorSelection(() => {
    schedule()
  })
  const contentDisposable = editor.onDidChangeModelContent(() => {
    schedule()
  })

  return {
    dispose() {
      cursorDisposable.dispose()
      selectionDisposable.dispose()
      contentDisposable.dispose()
      if (timer) clearTimeout(timer)
    },
  }
}

export function registerYamlSchemaCompletion(
  monaco: typeof Monaco,
  getSchema: () => JsonSchema | null,
  editor?: Monaco.editor.ICodeEditor,
  getUriReference?: () => UriReferenceCompletionOptions | null,
  getParameterCompletion?: () => ParameterCompletionOptions | null,
): Monaco.IDisposable {
  return monaco.languages.registerCompletionItemProvider('yaml', {
    triggerCharacters: [':', '-', '/', '.', '@', '!'],

    provideCompletionItems(model, position, _context, token) {
      if (editor && editorHasSelection(editor)) {
        return { suggestions: [] }
      }

      const rootSchema = getSchema()
      if (!rootSchema) return { suggestions: [] }

      const suggestions = buildYamlCompletionSuggestions(
        monaco,
        rootSchema,
        model,
        position,
        getUriReference?.() ?? null,
        getParameterCompletion?.() ?? null,
        token,
      )

      if (suggestions instanceof Promise) {
        return suggestions.then(items => ({
          suggestions: items,
          // URI-reference results come from a server search; mark incomplete so
          // Monaco re-queries as more path characters arrive rather than filtering
          // a stale cached list client-side.
          incomplete: getUriReference?.() != null,
        }))
      }

      return { suggestions }
    },
  })
}

// Exported for unit tests.
export const __testing = {
  buildPropertyInsertText,
  buildArrayItemInsertText,
  formatArrayItemInsertText,
  formatNestedSnippetInsert,
  arrayItemIndentFromContext,
  bodyLineLeadingSpaces,
  formatScalarArrayItemInsertText,
  needsLeadingSpaceAfterArrayDash,
  isEmptyScalarArrayItemLine,
  shouldOfferArrayItemObjectSnippets,
  oneOfConstDiscriminatorSuggestions,
  resolveOneOfPropertySchema,
  effectivePropertyRowIndent,
  expectedPropertyRowIndent,
  expectedArrayElementRowIndent,
  isAtPropertyRow,
  isAtArrayElementRow,
  formatPropertyInsertForSnippet,
  shouldAutoTriggerYamlSuggest,
  hasYamlCompletionSuggestions,
  buildYamlCompletionSuggestions,
  editorHasSelection,
  hideSuggestWidget,
  enclosingArrayItemKeyLineIndent,
  isWithinArrayItemObject,
  oneOfBranches,
  oneOfVariantLabel,
  resolveOneOfBranch,
  branchMatchesConstDiscriminators,
  unwrapSchema,
  unwrapSchemaForBuild,
  buildArrayItemLines,
  buildSnippetVariants,
  dedupeSnippetVariants,
  collectOneOfSites,
  keysForSnippet,
  completionContext,
  parentYamlContext,
  resolveTargetSchema,
  schemaAtPath,
  schemaPathOptions,
  schemaDefault,
  schemaFirstExample,
  schemaFirstArrayItemExample,
  inheritSchemaMetadata,
  schemaEnumValues,
  hasEnumSchema,
  hasBooleanSchema,
  hasScalarValueSuggestions,
  scalarSuggestionValues,
  hasMatchingScalarSuggestion,
  matchesEnumPrefix,
  shouldShowEnumSuggestion,
  extractTypedPropertyValue,
  hasNonWhitespaceAfterCursor,
  canSuggestEnumAtPosition,
  propertyValueStartColumn,
  scalarPlaceholder,
  snippetPreviewText,
  formatCompletionPreviewDetail,
  isArrayElementRow,
  existingKeysInScope,
  valueSuggestions,
  valueSuggestionsForBranch,
}
