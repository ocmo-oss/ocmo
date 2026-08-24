export type JsonSchema = Record<string, unknown>

export function asObject(value: unknown): JsonSchema | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as JsonSchema
    : null
}

export function resolveRef(schema: JsonSchema, root: JsonSchema): JsonSchema {
  const ref = schema.$ref
  if (typeof ref !== 'string' || !ref.startsWith('#/$defs/')) return schema
  const name = ref.slice('#/$defs/'.length)
  const defs = asObject(root.$defs)
  return defs ? asObject(defs[name]) ?? schema : schema
}

export function oneOfBranches(schema: JsonSchema | null, root: JsonSchema): JsonSchema[] {
  if (!schema) return []
  const current = resolveRef(schema, root)
  if (!Array.isArray(current.oneOf)) return []
  return current.oneOf
    .map(item => asObject(item))
    .filter((item): item is JsonSchema => item !== null && item.type !== 'null')
    .map(item => resolveRef(item, root))
}

export function hasOneOf(schema: JsonSchema | null, root: JsonSchema): boolean {
  return oneOfBranches(schema, root).length > 1
}

export function oneOfVariantLabel(branch: JsonSchema, index: number): string {
  if (typeof branch.title === 'string' && branch.title.trim()) {
    return branch.title.trim()
  }
  const props = asObject(branch.properties) ?? {}
  for (const [key, raw] of Object.entries(props)) {
    const prop = asObject(raw)
    if (prop?.const !== undefined) {
      return `${key}: ${prop.const}`
    }
  }
  if (typeof branch.description === 'string' && branch.description.trim()) {
    return branch.description.trim().split('\n')[0]
  }
  return `option ${index + 1}`
}

export function inheritSchemaMetadata(parent: JsonSchema, child: JsonSchema): JsonSchema {
  const merged: JsonSchema = { ...child }
  if (merged.examples === undefined && parent.examples !== undefined) {
    merged.examples = parent.examples
  }
  if (merged.default === undefined && parent.default !== undefined) {
    merged.default = parent.default
  }
  if (merged.enum === undefined && parent.enum !== undefined) {
    merged.enum = parent.enum
  }
  if (merged.description === undefined && parent.description !== undefined) {
    merged.description = parent.description
  }
  return merged
}

/**
 * Unwrap anyOf (picking first non-null branch) but NOT oneOf — oneOf is
 * resolved explicitly at completion boundaries.
 */
export function unwrapSchema(schema: JsonSchema | null, root: JsonSchema): JsonSchema | null {
  if (!schema) return null
  let current = resolveRef(schema, root)

  if (Array.isArray(current.anyOf)) {
    const parent = current
    for (const item of current.anyOf) {
      const candidate = unwrapSchema(asObject(item), root)
      if (candidate && candidate.type !== 'null') {
        return inheritSchemaMetadata(parent, candidate)
      }
    }
  }

  return current
}

export function isObjectSchema(schema: JsonSchema): boolean {
  return schema.type === 'object' || Boolean(asObject(schema.properties))
    || (schema.additionalProperties !== undefined && schema.additionalProperties !== false)
}

export function isArraySchema(schema: JsonSchema): boolean {
  return schema.type === 'array' || schema.items !== undefined
}

export function isNullable(schema: JsonSchema): boolean {
  if (schema.type === 'null') return true
  if (Array.isArray(schema.anyOf)) {
    return schema.anyOf.some(item => asObject(item)?.type === 'null')
  }
  return false
}

export function itemSchemaOf(schema: JsonSchema): JsonSchema | null {
  const items = schema.items
  if (!items) return null
  return Array.isArray(items) ? asObject(items[0]) : asObject(items)
}

export function schemaDefault(schema: JsonSchema): string | null {
  const value = schema.default
  if (value === undefined || value === null) return null
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return null
}

export function schemaFirstExample(schema: JsonSchema): string | null {
  if (!Array.isArray(schema.examples) || schema.examples.length === 0) return null
  const first = schema.examples[0]
  if (first === null || first === undefined) return null
  if (typeof first === 'string') return first
  if (typeof first === 'number' || typeof first === 'boolean') return String(first)
  return null
}

export function schemaFirstArrayItemExample(arraySchema: JsonSchema): string | null {
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

export const BOOLEAN_LITERALS = ['true', 'false'] as const

export function schemaDescription(schema: JsonSchema | null | undefined): string | undefined {
  if (!schema) return undefined
  if (typeof schema.description === 'string' && schema.description.trim()) {
    return schema.description.trim()
  }
  return undefined
}

// Note: schemaEnumValues, isBooleanSchema, hasBooleanSchema, hasScalarAnyOfSchema,
// hasScalarValueSuggestions, scalarSuggestionValues, matchesEnumPrefix,
// shouldShowEnumSuggestion, hasMatchingScalarSuggestion are NOT here because their
// implementations in yamlSchemaCompletion.ts use unwrapSchemaForBuild (snippet layer).
// They live in the provider split modules (completionItem.ts / provider.ts).
