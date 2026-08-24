import type * as Monaco from 'monaco-editor'
import type { YamlCompletionContext } from './types'
import { lineKey, stripYamlScalarQuotes } from './lineSyntax'
import { PARAMETER_NAME_PATTERN, parseOcmoParameters } from './ocmoParameterCompletion'
import { asObject, unwrapSchema, type JsonSchema } from './jsonSchema'

const PARAMETERS_KEY = 'parameters'

const RESERVED_PARAMETER_FIELD_NAMES = new Set([
  'type',
  'value',
  'description',
  'transformers',
])

function isParameterNameKey(key: string): boolean {
  return PARAMETER_NAME_PATTERN.test(key) && !RESERVED_PARAMETER_FIELD_NAMES.has(key)
}

export const PARAMETER_DECLARATION_FIELDS = [
  'type',
  'value',
  'description',
  'transformers',
] as const

export const PROJECTED_PARAMETER_SELECTORS = [
  { label: '.Path', description: 'Full path of the config' },
  { label: '.Name', description: 'Config name (last path segment)' },
  { label: '.Data', description: 'Value from config data (append .key.path)' },
  { label: '.Version.tag', description: 'Version reference tag used for resolve' },
  { label: '.Version.number', description: 'Resolved integer version number' },
] as const

export interface OcmoParameterDeclarationContext {
  parameterName: string
  objectPath: string[]
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
    const key = lineKey(content)
    if (key) {
      return lineIndent
    }
  }

  return 0
}

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

function findParametersAncestorPath(
  model: Monaco.editor.ITextModel,
  lineNumber: number,
  childIndent: number,
): string[] | null {
  for (let ln = lineNumber; ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    const key = lineKey(line)
    if (!key) continue
    const indent = line.search(/\S/)
    if (indent >= childIndent) continue
    if (key !== PARAMETERS_KEY) continue

    for (let ml = ln - 1; ml >= 1; ml--) {
      const mline = model.getLineContent(ml)
      const mkey = lineKey(mline)
      if (!mkey) continue
      const mindent = mline.search(/\S/)
      if (mindent < indent) {
        return [mkey, PARAMETERS_KEY]
      }
    }
    return null
  }
  return null
}

function findParameterNameIndent(
  model: Monaco.editor.ITextModel,
  parameterName: string,
  lineNumber: number,
): number {
  for (let ln = Math.min(lineNumber, model.getLineCount()); ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    if (lineKey(line) === parameterName) {
      return line.search(/\S/)
    }
  }
  return -1
}

/** Row indent from explicit whitespace only (never inferred from parent lines). */
function explicitPropertyRowIndent(
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
  return line.match(/^(\s*)/)?.[1].length ?? 0
}

export function isAtParameterFieldRow(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  declaration: OcmoParameterDeclarationContext,
): boolean {
  const line = model.getLineContent(position.lineNumber)
  const currentKey = lineKey(line)
  if (currentKey === declaration.parameterName) {
    return false
  }

  const paramIndent = findParameterNameIndent(
    model,
    declaration.parameterName,
    position.lineNumber,
  )
  if (paramIndent < 0) return false

  const expectedChildIndent = paramIndent + 2
  const rowIndent = explicitPropertyRowIndent(model, position.lineNumber, position.column)
  return rowIndent === expectedChildIndent
}

export function resolveParameterObjectPathFromIndent(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): OcmoParameterDeclarationContext | null {
  const lineNumber = position.lineNumber
  const line = model.getLineContent(lineNumber)
  const currentKey = lineKey(line)
  if (currentKey && isParameterNameKey(currentKey)) {
    return null
  }

  const rowIndent = explicitPropertyRowIndent(model, lineNumber, position.column)
  const parameterNameIndent = rowIndent - 2
  if (parameterNameIndent < 0) return null

  for (let ln = lineNumber - 1; ln >= 1; ln--) {
    const prev = model.getLineContent(ln)
    const trimmed = prev.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const indent = prev.search(/\S/)
    if (indent >= rowIndent) continue

    const key = lineKey(prev)
    if (key && indent === parameterNameIndent && isParameterNameKey(key)) {
      const ancestor = findParametersAncestorPath(model, ln, indent)
      if (ancestor) {
        return {
          parameterName: key,
          objectPath: [...ancestor, key],
        }
      }
      return null
    }

    if (indent < parameterNameIndent) break
  }

  return null
}

export function existingKeysInYamlObject(
  model: Monaco.editor.ITextModel,
  objectPath: string[],
  lineNumber = model.getLineCount(),
): Set<string> {
  const keys = new Set<string>()
  if (objectPath.length === 0) return keys

  const parentKey = objectPath[objectPath.length - 1]
  let parentIndent = -1
  let parentLineNumber = -1

  for (let ln = Math.min(lineNumber, model.getLineCount()); ln >= 1; ln--) {
    const line = model.getLineContent(ln)
    if (lineKey(line) === parentKey) {
      parentLineNumber = ln
      parentIndent = line.search(/\S/)
      break
    }
  }
  if (parentLineNumber < 0 || parentIndent < 0) return keys

  const childIndent = parentIndent + 2
  for (let ln = parentLineNumber + 1; ln <= model.getLineCount(); ln++) {
    const line = model.getLineContent(ln)
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const indent = line.search(/\S/)
    if (indent <= parentIndent) break
    if (indent === childIndent) {
      const key = lineKey(line)
      if (key) keys.add(key)
    }
  }

  return keys
}

export function resolveParameterDeclarationSchema(
  rootSchema: JsonSchema,
  objectPath: string[],
): JsonSchema | null {
  if (objectPath.length < 3 || objectPath[1] !== PARAMETERS_KEY) return null

  const metadataSchema = unwrapSchema(
    asObject(asObject(rootSchema.properties)?.[objectPath[0]]),
    rootSchema,
  )
  if (!metadataSchema) return null

  const parametersSchema = unwrapSchema(
    asObject(asObject(metadataSchema.properties)?.parameters),
    rootSchema,
  )
  if (!parametersSchema) return null

  const additional = parametersSchema.additionalProperties
  if (additional && typeof additional === 'object') {
    return unwrapSchema(asObject(additional), rootSchema)
  }

  return null
}

export function parameterDeclarationMissingFields(
  rootSchema: JsonSchema | null,
  objectPath: string[],
  existingKeys: Set<string>,
): string[] {
  const schema = rootSchema ? resolveParameterDeclarationSchema(rootSchema, objectPath) : null
  const properties = schema
    ? Object.keys(asObject(unwrapSchema(schema, rootSchema!)?.properties) ?? {})
    : [...PARAMETER_DECLARATION_FIELDS]

  return properties.filter(name => !existingKeys.has(name))
}

function propertyValueStartColumn(line: string): number | null {
  const colon = line.indexOf(':')
  if (colon < 0) return null
  let start = colon + 1
  while (start < line.length && /\s/.test(line[start] ?? '')) {
    start += 1
  }
  return start + 1
}

function propertyValueEndColumn(line: string, valueStartColumn: number): number {
  let pos = valueStartColumn - 1
  while (pos < line.length && /\s/.test(line[pos] ?? '')) {
    pos += 1
  }
  if (pos >= line.length) {
    return valueStartColumn
  }

  const first = line[pos]
  if (first === '"' || first === "'") {
    const quote = first
    for (let index = line.length - 1; index > pos; index--) {
      const ch = line[index]
      if (ch === quote && line[index - 1] !== '\\') {
        return index + 2
      }
    }
    return line.length + 1
  }

  let end = line.length
  const comment = line.indexOf(' #', pos)
  if (comment >= 0) {
    end = comment
  }
  while (end > pos && /\s/.test(line[end - 1] ?? '')) {
    end -= 1
  }
  return end + 1
}

export function propertyValueCompletionRange(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): Monaco.IRange | null {
  const line = model.getLineContent(position.lineNumber)
  const start = propertyValueStartColumn(line)
  if (start === null) return null
  const end = propertyValueEndColumn(line, start)
  return {
    startLineNumber: position.lineNumber,
    startColumn: start,
    endLineNumber: position.lineNumber,
    endColumn: Math.max(start, end),
  }
}

function fullPropertyValueAtPosition(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): { typedBefore: string; fullValue: string } {
  const line = model.getLineContent(position.lineNumber)
  const start = propertyValueStartColumn(line)
  if (start === null) {
    return { typedBefore: '', fullValue: '' }
  }
  const end = propertyValueEndColumn(line, start)
  const raw = model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: start,
    endLineNumber: position.lineNumber,
    endColumn: end,
  })
  const fullValue = stripYamlScalarQuotes(raw)
  const typedBefore = stripYamlScalarQuotes(model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: start,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  }))
  return { typedBefore, fullValue }
}

function shouldShowProjectedSelectorSuggestion(
  selector: string,
  typedBefore: string,
  _fullValue: string,
): boolean {
  const selectorLower = selector.toLowerCase()
  const typedLower = typedBefore.toLowerCase()

  if (typedLower === selectorLower) {
    return false
  }
  if (!typedLower) {
    return true
  }
  return selectorLower.startsWith(typedLower)
}

export function isOcmoParameterDeclarationObjectPath(
  objectPath: string[],
  metadataKey?: string | null,
): boolean {
  return objectPath.length >= 3
    && objectPath[1] === PARAMETERS_KEY
    && (!metadataKey || objectPath[0] === metadataKey)
    && isParameterNameKey(objectPath[2])
}

export function canSuggestInParameterDeclarationObject(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  objectPath: string[],
  metadataKey?: string | null,
): boolean {
  if (!isOcmoParameterDeclarationObjectPath(objectPath, metadataKey)) {
    return true
  }
  return isAtParameterFieldRow(model, position, {
    parameterName: objectPath[2],
    objectPath: objectPath.slice(0, 3),
  })
}

export function detectOcmoParameterDeclarationContext(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
  metadataKey?: string | null,
): OcmoParameterDeclarationContext | null {
  const fromIndent = resolveParameterObjectPathFromIndent(model, position)
  if (fromIndent) {
    return fromIndent
  }

  if (
    ctx.objectPath.length >= 3
    && ctx.objectPath[1] === PARAMETERS_KEY
    && isParameterNameKey(ctx.objectPath[2])
    && (!metadataKey || ctx.objectPath[0] === metadataKey)
    && isAtParameterFieldRow(model, position, {
      parameterName: ctx.objectPath[2],
      objectPath: ctx.objectPath.slice(0, 3),
    })
  ) {
    return {
      parameterName: ctx.objectPath[2],
      objectPath: ctx.objectPath.slice(0, 3),
    }
  }

  return null
}

export function detectOcmoParameterValueContext(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
  metadataKey?: string | null,
): OcmoParameterDeclarationContext | null {
  if (ctx.kind !== 'property-value' || ctx.valuePropertyKey !== 'value') {
    return null
  }
  return detectOcmoParameterDeclarationContext(model, position, ctx, metadataKey)
}

export function readOcmoParameterType(
  model: Monaco.editor.ITextModel,
  metadataKey: string,
  parameterName: string,
): string | undefined {
  return parseOcmoParameters(model.getValue(), metadataKey)
    .find(param => param.name === parameterName)
    ?.type
}

export function shouldSuggestParameterDeclarationFields(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
  metadataKey: string | null | undefined,
  rootSchema: JsonSchema | null,
): boolean {
  if (ctx.kind !== 'property-key') return false
  const declaration = detectOcmoParameterDeclarationContext(model, position, ctx, metadataKey)
  if (!declaration || !isAtParameterFieldRow(model, position, declaration)) {
    return false
  }
  const existingKeys = existingKeysInYamlObject(
    model,
    declaration.objectPath,
    position.lineNumber,
  )
  return parameterDeclarationMissingFields(rootSchema, declaration.objectPath, existingKeys).length > 0
}

export function shouldSuggestParameterValue(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
  metadataKey?: string | null,
): boolean {
  const declaration = detectOcmoParameterValueContext(model, position, ctx, metadataKey)
  if (!declaration) return false

  const parameterType = readOcmoParameterType(
    model,
    declaration.objectPath[0],
    declaration.parameterName,
  )
  if (parameterType === 'dynamic') return false
  if (parameterType === 'projected') {
    const { typedBefore, fullValue } = fullPropertyValueAtPosition(model, position)
    return PROJECTED_PARAMETER_SELECTORS.some(selector => (
      shouldShowProjectedSelectorSuggestion(selector.label, typedBefore, fullValue)
    ))
  }
  if (parameterType === 'secret') return true
  return false
}

export function buildParameterProjectedValueSuggestions(
  monaco: typeof Monaco,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  range?: Monaco.IRange,
): Monaco.languages.CompletionItem[] {
  const completionRange = range ?? propertyValueCompletionRange(model, position)
  if (!completionRange) return []

  const { typedBefore, fullValue } = fullPropertyValueAtPosition(model, position)
  return PROJECTED_PARAMETER_SELECTORS
    .filter(selector => shouldShowProjectedSelectorSuggestion(
      selector.label,
      typedBefore,
      fullValue,
    ))
    .map((selector, index) => ({
      label: { label: selector.label, description: 'projected selector' },
      kind: monaco.languages.CompletionItemKind.Value,
      insertText: selector.label,
      range: completionRange,
      filterText: selector.label,
      sortText: `!${index.toString().padStart(3, '0')}:${selector.label}`,
      detail: 'projected',
      documentation: {
        value: selector.description,
        isTrusted: true,
      },
    }))
}

export const __testingParameterDeclarationCompletion = {
  readOcmoParameterType,
  resolveParameterObjectPathFromIndent,
  existingKeysInYamlObject,
  resolveParameterDeclarationSchema,
  effectivePropertyRowIndent,
  inferredPropertyRowIndent,
  isAtParameterFieldRow,
  canSuggestInParameterDeclarationObject,
  propertyValueCompletionRange,
  fullPropertyValueAtPosition,
  shouldShowProjectedSelectorSuggestion,
}
