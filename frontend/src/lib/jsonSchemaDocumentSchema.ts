/**
 * JSON Schema document shape and type-specific keyword subsets for editor autocomplete.
 */

const TYPE_ENUM = ['object', 'array', 'string', 'number', 'integer', 'boolean', 'null'] as const

const typeKeyword = {
  description: 'Instance type(s) this schema applies to.',
  anyOf: [
    { type: 'string', enum: [...TYPE_ENUM] },
    {
      type: 'array',
      items: { type: 'string', enum: [...TYPE_ENUM] },
      minItems: 1,
    },
  ],
}

const descriptionKeyword = {
  type: 'string',
  description: 'Longer description of the schema.',
}

const titleKeyword = {
  type: 'string',
  description: 'Short title for the schema.',
}

const deprecatedKeyword = {
  type: 'boolean',
  description: 'Mark the schema or keyword as deprecated.',
}

const examplesKeyword = {
  type: 'array',
  description: 'Example valid instances.',
}

const defaultKeyword = {
  description: 'Default value when the instance is absent.',
}

const constKeyword = {
  description: 'Single allowed value.',
}

const enumKeyword = {
  type: 'array',
  description: 'Allowed values.',
  minItems: 1,
}

function keywordProperties(
  entries: Record<string, unknown>,
): Record<string, unknown> {
  return entries
}

/** Keywords suggested before `type` is set on a property subschema. */
export const jsonSchemaUntypedPropertyKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
})

/** Document root keywords (after the base template is inserted). */
export const jsonSchemaDocumentRootKeywords = keywordProperties({
  $schema: {
    type: 'string',
    description: 'JSON Schema dialect identifier.',
    examples: ['https://json-schema.org/draft/2020-12/schema'],
  },
  $id: {
    type: 'string',
    description: 'Canonical URI of the schema.',
  },
  title: titleKeyword,
  description: descriptionKeyword,
  type: typeKeyword,
  additionalProperties: {
    description: 'Whether extra object properties are allowed.',
    anyOf: [
      { type: 'boolean' },
      { $ref: '#/$defs/JsonSchemaUntyped' },
    ],
  },
  required: {
    type: 'array',
    description: 'Required property names.',
    items: { type: 'string', minLength: 1 },
  },
  properties: {
    type: 'object',
    description: 'Property definitions when type is object.',
    additionalProperties: { $ref: '#/$defs/JsonSchemaUntyped' },
  },
  $defs: {
    type: 'object',
    description: 'Reusable subschema definitions.',
    additionalProperties: { $ref: '#/$defs/JsonSchemaUntyped' },
  },
})

const stringKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
  pattern: {
    type: 'string',
    description: 'Regular expression the string value must match.',
  },
  format: {
    type: 'string',
    description: 'Semantic format hint (e.g. uri, email, date-time).',
  },
  minLength: { type: 'integer', minimum: 0 },
  maxLength: { type: 'integer', minimum: 0 },
  enum: enumKeyword,
  const: constKeyword,
  default: defaultKeyword,
  examples: examplesKeyword,
  deprecated: deprecatedKeyword,
})

const numberKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
  minimum: { type: 'number' },
  maximum: { type: 'number' },
  exclusiveMinimum: { type: 'number' },
  exclusiveMaximum: { type: 'number' },
  multipleOf: { type: 'number', exclusiveMinimum: 0 },
  enum: enumKeyword,
  const: constKeyword,
  default: defaultKeyword,
  examples: examplesKeyword,
  deprecated: deprecatedKeyword,
})

const booleanKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
  default: defaultKeyword,
  examples: examplesKeyword,
  deprecated: deprecatedKeyword,
})

const objectKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
  properties: {
    type: 'object',
    description: 'Nested property definitions.',
    additionalProperties: { $ref: '#/$defs/JsonSchemaUntyped' },
  },
  required: {
    type: 'array',
    description: 'Required property names.',
    items: { type: 'string', minLength: 1 },
  },
  additionalProperties: {
    description: 'Whether extra object properties are allowed.',
    anyOf: [
      { type: 'boolean' },
      { $ref: '#/$defs/JsonSchemaUntyped' },
    ],
  },
  minProperties: { type: 'integer', minimum: 0 },
  maxProperties: { type: 'integer', minimum: 0 },
  deprecated: deprecatedKeyword,
})

const arrayKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
  items: {
    description: 'Schema for array items.',
    $ref: '#/$defs/JsonSchemaUntyped',
  },
  minItems: { type: 'integer', minimum: 0 },
  maxItems: { type: 'integer', minimum: 0 },
  uniqueItems: { type: 'boolean' },
  deprecated: deprecatedKeyword,
})

const nullKeywords = keywordProperties({
  type: typeKeyword,
  title: titleKeyword,
  description: descriptionKeyword,
  deprecated: deprecatedKeyword,
})

const TYPE_KEYWORD_MAP: Record<string, Record<string, unknown>> = {
  string: stringKeywords,
  number: numberKeywords,
  integer: numberKeywords,
  boolean: booleanKeywords,
  object: objectKeywords,
  array: arrayKeywords,
  null: nullKeywords,
}

export function subschemaKeywordsForInstanceType(
  instanceType: string | null | undefined,
): Record<string, unknown> {
  if (!instanceType) {
    return jsonSchemaUntypedPropertyKeywords
  }
  return TYPE_KEYWORD_MAP[instanceType] ?? jsonSchemaUntypedPropertyKeywords
}

export function subschemaForInstanceType(
  instanceType: string | null | undefined,
): Record<string, unknown> {
  return {
    type: 'object',
    properties: subschemaKeywordsForInstanceType(instanceType),
    additionalProperties: false,
  }
}

export const JSON_SCHEMA_DOCUMENT_MARKER = 'x-ocmo-json-schema-document'

export const jsonSchemaDocumentSchema: Record<string, unknown> = {
  [JSON_SCHEMA_DOCUMENT_MARKER]: true,
  $defs: {
    JsonSchemaUntyped: {
      title: 'JSON Schema property',
      type: 'object',
      properties: jsonSchemaUntypedPropertyKeywords,
      additionalProperties: false,
    },
  },
  type: 'object',
  properties: jsonSchemaDocumentRootKeywords,
  additionalProperties: false,
}
