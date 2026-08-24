import type * as Monaco from 'monaco-editor'
import type { YamlCompletionContext } from './types'
import { formatYamlScalar, needsYamlQuoting } from '../yamlScalar'
import { isScalarArrayItemLine, arrayItemValueStartColumn } from './lineSyntax'

export const PARAMETER_NAME_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_]*$/
const PLACEHOLDER_PARTIAL_RE = /\{!([a-zA-Z_][a-zA-Z0-9_]*)?$/
const USER_CLAIM_PLACEHOLDER_RE = /\{!user(\.[a-zA-Z0-9_]*)?$/

export interface ParameterCompletionOptions {
  metadataKey: string
}

export interface OcmoParameterDeclaration {
  name: string
  description?: string
  type?: string
}

function parseScalarYamlValue(raw: string): string {
  const trimmed = raw.trim()
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"'))
    || (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

function completionDocumentation(
  description: string | undefined,
): { value: string; isTrusted?: boolean } | undefined {
  if (!description?.trim()) return undefined
  return { value: description.trim(), isTrusted: true }
}

interface YamlValueSpan {
  quote: 'none' | 'single' | 'double'
  content: string
  spanStart: number
  spanEnd: number
}

export interface ParameterPlaceholderContext {
  partialName: string
  replaceStartColumn: number
  replaceEndColumn: number
  valueSpan: YamlValueSpan
  hasClosingBrace: boolean
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


function yamlValueSpan(line: string, valueStartColumn: number): YamlValueSpan | null {
  if (valueStartColumn < 1) return null
  let pos = valueStartColumn - 1
  while (pos < line.length && /\s/.test(line[pos] ?? '')) {
    pos += 1
  }
  if (pos >= line.length) {
    return {
      quote: 'none',
      content: '',
      spanStart: pos + 1,
      spanEnd: pos + 1,
    }
  }

  const first = line[pos]
  if (first === '"' || first === "'") {
    const quote = first === '"' ? 'double' : 'single'
    const contentStart = pos + 1
    let end = line.length
    for (let index = line.length - 1; index > contentStart; index--) {
      const ch = line[index]
      if (ch === first && line[index - 1] !== '\\') {
        end = index
        break
      }
    }
    return {
      quote,
      content: line.slice(contentStart, end),
      spanStart: pos + 1,
      spanEnd: end + 1,
    }
  }

  let end = line.length
  const comment = line.indexOf(' #', pos)
  if (comment >= 0) {
    end = comment
  }
  while (end > pos && /\s/.test(line[end - 1] ?? '')) {
    end -= 1
  }

  return {
    quote: 'none',
    content: line.slice(pos, end),
    spanStart: pos + 1,
    spanEnd: end + 1,
  }
}

function escapeQuotedContent(content: string, quote: 'single' | 'double'): string {
  if (quote === 'double') {
    return content
      .replace(/\\/g, '\\\\')
      .replace(/"/g, '\\"')
  }
  return content.replace(/'/g, "''")
}

function formatParameterValueForInsert(
  content: string,
  quote: YamlValueSpan['quote'],
): string {
  const usesParameter = /\{![a-zA-Z_][a-zA-Z0-9_]*\}/.test(content)
    || PLACEHOLDER_PARTIAL_RE.test(content)

  if (usesParameter) {
    if (quote === 'none') {
      return formatYamlScalar(content)
    }
    const q = quote === 'double' ? '"' : "'"
    return `${q}${escapeQuotedContent(content, quote)}${q}`
  }

  if (quote === 'none' && needsYamlQuoting(content)) {
    return formatYamlScalar(content)
  }
  if (quote !== 'none') {
    const q = quote === 'double' ? '"' : "'"
    return `${q}${escapeQuotedContent(content, quote)}${q}`
  }
  return content
}

export function parseOcmoParameters(
  yamlContent: string,
  metadataKey: string,
): OcmoParameterDeclaration[] {
  const parameters: OcmoParameterDeclaration[] = []
  const byName = new Map<string, OcmoParameterDeclaration>()
  let inMetadata = false
  let inParameters = false
  let metadataIndent = -1
  let parametersIndent = -1
  let currentParam: OcmoParameterDeclaration | null = null
  let currentParamIndent = -1

  for (const line of yamlContent.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue

    const indent = line.search(/\S/)
    const keyMatch = trimmed.match(/^["']?([\w@./_-]+)["']?\s*:(.*)$/)
    const key = keyMatch?.[1]
    const rawValue = keyMatch?.[2] ?? ''

    if (!inMetadata) {
      if (key === metadataKey) {
        inMetadata = true
        metadataIndent = indent
      }
      continue
    }

    if (indent <= metadataIndent) {
      break
    }

    if (!inParameters) {
      if (key === 'parameters' && indent > metadataIndent) {
        inParameters = true
        parametersIndent = indent
      }
      continue
    }

    if (indent <= parametersIndent) {
      break
    }

    if (indent === parametersIndent + 2 && key && PARAMETER_NAME_PATTERN.test(key)) {
      currentParam = byName.get(key) ?? { name: key }
      if (!byName.has(key)) {
        byName.set(key, currentParam)
        parameters.push(currentParam)
      }
      currentParamIndent = indent
      continue
    }

    if (!currentParam || indent <= currentParamIndent) {
      currentParam = null
      currentParamIndent = -1
      continue
    }

    if (key === 'description') {
      const description = parseScalarYamlValue(rawValue)
      if (description) {
        currentParam.description = description
      }
      continue
    }

    if (key === 'type') {
      const type = parseScalarYamlValue(rawValue)
      if (type) {
        currentParam.type = type
      }
    }
  }

  return parameters
}

export function parseOcmoParameterNames(
  yamlContent: string,
  metadataKey: string,
): string[] {
  return parseOcmoParameters(yamlContent, metadataKey).map(param => param.name)
}

export function detectParameterPlaceholderContext(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
): ParameterPlaceholderContext | null {
  const line = model.getLineContent(position.lineNumber)
  let valueStartColumn: number | null = null

  if (ctx.kind === 'property-value') {
    valueStartColumn = propertyValueStartColumn(line)
  } else if (ctx.kind === 'array-item' && isScalarArrayItemLine(line)) {
    valueStartColumn = arrayItemValueStartColumn(line)
  } else {
    return null
  }

  if (valueStartColumn === null || position.column < valueStartColumn) {
    return null
  }

  const valueSpan = yamlValueSpan(line, valueStartColumn)
  if (!valueSpan) return null

  const offsetInContent = position.column - valueSpan.spanStart
  if (offsetInContent < 0 || offsetInContent > valueSpan.content.length) {
    return null
  }

  const before = valueSpan.content.slice(0, offsetInContent)
  if (USER_CLAIM_PLACEHOLDER_RE.test(before)) {
    return null
  }

  const match = before.match(PLACEHOLDER_PARTIAL_RE)
  if (!match) return null

  const afterInContent = valueSpan.content.slice(offsetInContent)
  const hasClosingBrace = afterInContent.startsWith('}')

  return {
    partialName: match[1] ?? '',
    replaceStartColumn: valueSpan.spanStart + before.length - match[0].length,
    replaceEndColumn: hasClosingBrace
      ? position.column
      : position.column,
    valueSpan,
    hasClosingBrace,
  }
}

export function shouldSuggestParameterPlaceholders(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
  options: ParameterCompletionOptions,
): boolean {
  if (ctx.kind !== 'property-value' && ctx.kind !== 'array-item') {
    return false
  }
  const names = parseOcmoParameterNames(model.getValue(), options.metadataKey)
  if (names.length === 0) return false
  return detectParameterPlaceholderContext(model, position, ctx) !== null
}

export function buildParameterPlaceholderSuggestions(
  monaco: typeof Monaco,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
  ctx: YamlCompletionContext,
  options: ParameterCompletionOptions,
): Monaco.languages.CompletionItem[] {
  const placeholderCtx = detectParameterPlaceholderContext(model, position, ctx)
  if (!placeholderCtx) return []

  const declared = parseOcmoParameters(model.getValue(), options.metadataKey)
  if (declared.length === 0) return []

  const partial = placeholderCtx.partialName.toLowerCase()
  const matches = declared.filter(param => {
    if (!partial) return true
    if (param.name.toLowerCase() === partial) return false
    return param.name.toLowerCase().startsWith(partial)
  })
  if (matches.length === 0) return []

  const { valueSpan, hasClosingBrace } = placeholderCtx
  const offsetInContent = position.column - valueSpan.spanStart
  const before = valueSpan.content.slice(0, offsetInContent)
  const placeholderMatch = before.match(PLACEHOLDER_PARTIAL_RE)
  if (!placeholderMatch) return []

  const replaceStartInContent = before.length - placeholderMatch[0].length
  const afterInContent = valueSpan.content.slice(offsetInContent)
  const afterSuffix = hasClosingBrace ? afterInContent : `}${afterInContent}`

  return matches.map((param, index) => {
    const name = param.name
    const placeholderBody = `{!${name}`
    const newContent = valueSpan.content.slice(0, replaceStartInContent)
      + placeholderBody
      + afterSuffix
    const insertText = formatParameterValueForInsert(newContent, valueSpan.quote)
    const placeholderLabel = `{!${name}}`

    const documentationParts: string[] = []
    if (param.type) {
      documentationParts.push(`**Type:** ${param.type}`)
    }
    if (param.description) {
      documentationParts.push(param.description)
    }
    if (documentationParts.length === 0) {
      documentationParts.push(`Declared in \`${options.metadataKey}.parameters\`.`)
    }

    return {
      label: { label: name, description: placeholderLabel },
      kind: monaco.languages.CompletionItemKind.Variable,
      insertText,
      range: {
        startLineNumber: position.lineNumber,
        startColumn: valueSpan.spanStart,
        endLineNumber: position.lineNumber,
        endColumn: valueSpan.spanEnd,
      },
      filterText: `${name} ${placeholderLabel}`,
      sortText: `!${index.toString().padStart(3, '0')}:${name}`,
      detail: 'parameter',
      documentation: completionDocumentation(documentationParts.join('\n\n')),
    }
  })
}

export const __testingParameterCompletion = {
  parseOcmoParameters,
  parseOcmoParameterNames,
  detectParameterPlaceholderContext,
  formatParameterValueForInsert,
  yamlValueSpan,
}
