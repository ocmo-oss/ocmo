import { jsonSchemaDocumentSchema, JSON_SCHEMA_DOCUMENT_MARKER } from './jsonSchemaDocumentSchema'

export function configEditorModelPath(namespace: string, path: string): string {
  return `config-editor/${namespace}/${path}.yaml`
}

export function createItemEditorModelPath(namespace: string, kind: string): string {
  return `${kind}-editor/${namespace}/__create__.yaml`
}

function collectDefs(schema: Record<string, unknown>, defs: Record<string, unknown>): void {
  const schemaDefs = schema.$defs
  if (schemaDefs && typeof schemaDefs === 'object' && !Array.isArray(schemaDefs)) {
    Object.assign(defs, schemaDefs as Record<string, unknown>)
  }
}

function withoutDefs(schema: Record<string, unknown>): Record<string, unknown> {
  const { $defs: _defs, ...rest } = schema
  return rest
}

/** Limit `_ocmo` autocomplete to keys valid for the current editor mode. */
export function filterMetadataSchemaForEditor(
  ocmoSchema: Record<string, unknown>,
  isJsonSchemaMode: boolean,
): Record<string, unknown> {
  const properties = ocmoSchema.properties
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) {
    return ocmoSchema
  }

  const props = properties as Record<string, unknown>
  const filtered: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(props)) {
    if (isJsonSchemaMode && key !== 'is_json_schema') {
      continue
    }
    filtered[key] = value
  }

  return { ...ocmoSchema, properties: filtered }
}

export interface BuildConfigEditorSchemaOptions {
  isJsonSchemaMode?: boolean
  /** Use *dataSchema* as-is instead of the generic JSON Schema document template. */
  useExplicitDataSchema?: boolean
}

export function buildConfigEditorSchema(
  metadataKey: string,
  ocmoSchema: Record<string, unknown>,
  dataSchema: Record<string, unknown> | null,
  options: BuildConfigEditorSchemaOptions = {},
): Record<string, unknown> {
  const isJsonSchemaMode = options.isJsonSchemaMode ?? false
  const metadataSchema = filterMetadataSchemaForEditor(ocmoSchema, isJsonSchemaMode)
  const effectiveDataSchema = options.useExplicitDataSchema
    ? dataSchema
    : (isJsonSchemaMode ? jsonSchemaDocumentSchema : dataSchema)

  const defs: Record<string, unknown> = {}
  collectDefs(metadataSchema, defs)
  if (effectiveDataSchema) collectDefs(effectiveDataSchema, defs)

  const properties: Record<string, unknown> = {
    [metadataKey]: withoutDefs(metadataSchema),
  }

  if (effectiveDataSchema) {
    const dataProps = effectiveDataSchema.properties
    if (dataProps && typeof dataProps === 'object') {
      Object.assign(properties, dataProps)
    }
  }

  const schema: Record<string, unknown> = {
    type: 'object',
    properties,
  }

  if (Object.keys(defs).length > 0) {
    schema.$defs = defs
  }
  if (effectiveDataSchema?.required && Array.isArray(effectiveDataSchema.required)) {
    schema.required = effectiveDataSchema.required
  }
  if (effectiveDataSchema && 'additionalProperties' in effectiveDataSchema) {
    schema.additionalProperties = effectiveDataSchema.additionalProperties
  }
  if (isJsonSchemaMode) {
    schema[JSON_SCHEMA_DOCUMENT_MARKER] = true
  }

  return schema
}
