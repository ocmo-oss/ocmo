import type * as Monaco from 'monaco-editor'
import {
  JSON_SCHEMA_DOCUMENT_MARKER,
  subschemaForInstanceType,
} from '../jsonSchemaDocumentSchema'
import { lineKey } from './lineSyntax'
import { escapeMonacoSnippetDollars } from './monacoSnippet'
import type { YamlCompletionContext } from './types'
import type { JsonSchema } from './jsonSchema'

export const JSON_SCHEMA_ROOT_SNIPPET_LABEL = 'JSON Schema document (base structure)'

export const JSON_SCHEMA_ROOT_SNIPPET_BODY = [
  '$schema: https://json-schema.org/draft/2020-12/schema',
  'title: ${1:Data title}',
  'description: ${2:Data structure description}',
  'type: object',
  'additionalProperties: false',
  'required: []',
  'properties: {}',
].join('\n')

function stripYamlScalarQuotes(value: string): string {
  return value.replace(/^['"]|['"]$/g, '')
}

function readYamlObjectFieldValue(
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

export function isJsonSchemaDocumentSchema(schema: JsonSchema | null): boolean {
  return Boolean(schema?.[JSON_SCHEMA_DOCUMENT_MARKER])
}

export function isJsonSchemaDocumentRootContext(
  ctx: YamlCompletionContext,
  metadataKey = '_ocmo',
  lineContent = '',
  column = 1,
): boolean {
  if (ctx.insideArrayItem) return false
  if (ctx.kind !== 'property-key') return false
  if (ctx.objectPath.length === 0) {
    return ctx.propertyRowSpaces <= 2
  }
  if (
    ctx.objectPath.length === 1
    && ctx.objectPath[0] === metadataKey
    && lineContent.trim() === ''
    && column <= 1
  ) {
    return true
  }
  return false
}

export function isJsonSchemaSubschemaContext(objectPath: string[]): boolean {
  if (objectPath.length < 2) return false
  const parent = objectPath[objectPath.length - 2]
  return parent === 'properties'
    || parent === 'items'
    || parent === '$defs'
    || parent === 'oneOf'
    || parent === 'anyOf'
    || parent === 'allOf'
}

export function hasYamlRootKey(model: Monaco.editor.ITextModel, key: string): boolean {
  for (let ln = 1; ln <= model.getLineCount(); ln++) {
    const line = model.getLineContent(ln)
    if (line.search(/\S/) !== 0) continue
    if (lineKey(line) === key) return true
  }
  return false
}

/** True when the document already has an inserted JSON Schema base structure. */
export function hasJsonSchemaBaseStructure(model: Monaco.editor.ITextModel): boolean {
  if (hasYamlRootKey(model, '$schema')) return true
  return hasYamlRootKey(model, 'type') && hasYamlRootKey(model, 'properties')
}

export function shouldOfferJsonSchemaRootSnippet(model: Monaco.editor.ITextModel): boolean {
  return !hasJsonSchemaBaseStructure(model)
}

export function buildJsonSchemaRootSnippetSuggestion(
  monaco: typeof Monaco,
  range: Monaco.IRange,
  indentPrefix: string,
): Monaco.languages.CompletionItem {
  return {
    label: JSON_SCHEMA_ROOT_SNIPPET_LABEL,
    kind: monaco.languages.CompletionItemKind.Snippet,
    insertText: escapeMonacoSnippetDollars(indentPrefix + JSON_SCHEMA_ROOT_SNIPPET_BODY),
    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
    range,
    filterText: 'json schema document base structure',
    sortText: '!000:json-schema-root',
    detail: 'snippet',
    documentation: {
      value: 'Insert a draft 2020-12 object schema with empty `required` and `properties`.',
      isTrusted: true,
    },
  }
}

export function resolveJsonSchemaTargetSchema(
  rootSchema: JsonSchema,
  targetSchema: JsonSchema | null,
  ctx: YamlCompletionContext,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): JsonSchema | null {
  if (!targetSchema || !isJsonSchemaDocumentSchema(rootSchema)) {
    return targetSchema
  }
  if (!isJsonSchemaSubschemaContext(ctx.objectPath)) {
    return targetSchema
  }
  const instanceType = readYamlObjectFieldValue(
    model,
    position.lineNumber,
    ctx.objectPath,
    'type',
  )
  return subschemaForInstanceType(instanceType) as JsonSchema
}
