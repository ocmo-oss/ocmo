export type MarkdownAction =
  | 'bold'
  | 'italic'
  | 'strike'
  | 'heading'
  | 'link'
  | 'ul'
  | 'ol'
  | 'code'
  | 'codeBlock'
  | 'quote'
  | 'hr'

export interface MarkdownEditResult {
  value: string
  selectionStart: number
  selectionEnd: number
}

function collapsedCaret(position: number): Pick<MarkdownEditResult, 'selectionStart' | 'selectionEnd'> {
  return { selectionStart: position, selectionEnd: position }
}

function wrapSelection(
  value: string,
  start: number,
  end: number,
  prefix: string,
  suffix: string,
  placeholder: string,
): MarkdownEditResult {
  const selected = value.slice(start, end)
  const hadSelection = start !== end
  const content = selected || placeholder
  const newValue = value.slice(0, start) + prefix + content + suffix + value.slice(end)
  const innerStart = start + prefix.length

  if (hadSelection) {
    return {
      value: newValue,
      selectionStart: innerStart,
      selectionEnd: innerStart + content.length,
    }
  }

  return {
    value: newValue,
    ...collapsedCaret(innerStart),
  }
}

function lineBounds(value: string, start: number, end: number) {
  const lineStart = value.lastIndexOf('\n', start - 1) + 1
  const nextNewline = value.indexOf('\n', end)
  const lineEnd = nextNewline === -1 ? value.length : nextNewline
  return { lineStart, lineEnd }
}

function lineIndexWithinBlock(value: string, lineStart: number, position: number): number {
  return Math.max(0, value.slice(lineStart, position).split('\n').length - 1)
}

function offsetWithinBlock(lines: string[], lineIndex: number): number {
  return lines.slice(0, lineIndex).join('\n').length + (lineIndex > 0 ? 1 : 0)
}

function caretOnPrefixedLine(
  lineStart: number,
  lines: string[],
  lineIndex: number,
  prefix: string,
): number {
  const lineText = lines[lineIndex] ?? ''
  return lineStart + offsetWithinBlock(lines, lineIndex) + prefix.length + lineText.length
}

function prefixLines(
  value: string,
  start: number,
  end: number,
  prefix: string,
): MarkdownEditResult {
  const hadSelection = start !== end
  const { lineStart, lineEnd } = lineBounds(value, start, end)
  const block = value.slice(lineStart, lineEnd)
  const lines = block.length === 0 ? [''] : block.split('\n')
  const prefixed = lines.map(line => `${prefix}${line}`).join('\n')
  const newValue = value.slice(0, lineStart) + prefixed + value.slice(lineEnd)

  if (!hadSelection) {
    const lineIndex = lineIndexWithinBlock(value, lineStart, start)
    return {
      value: newValue,
      ...collapsedCaret(caretOnPrefixedLine(lineStart, lines, lineIndex, prefix)),
    }
  }

  return {
    value: newValue,
    selectionStart: lineStart,
    selectionEnd: lineStart + prefixed.length,
  }
}

export function applyMarkdownAction(
  value: string,
  selectionStart: number,
  selectionEnd: number,
  action: MarkdownAction,
): MarkdownEditResult {
  const boundedStart = Math.max(0, Math.min(selectionStart, value.length))
  const boundedEnd = Math.max(0, Math.min(selectionEnd, value.length))
  const start = Math.min(boundedStart, boundedEnd)
  const end = Math.max(boundedStart, boundedEnd)
  const hadSelection = start !== end

  switch (action) {
    case 'bold':
      return wrapSelection(value, start, end, '**', '**', 'text')
    case 'italic':
      return wrapSelection(value, start, end, '*', '*', 'text')
    case 'strike':
      return wrapSelection(value, start, end, '~~', '~~', 'text')
    case 'code':
      return wrapSelection(value, start, end, '`', '`', 'code')
    case 'heading':
      return prefixLines(value, start, end, '## ')
    case 'quote':
      return prefixLines(value, start, end, '> ')
    case 'ul':
      return prefixLines(value, start, end, '- ')
    case 'ol':
      const { lineStart, lineEnd } = lineBounds(value, start, end)
      const block = value.slice(lineStart, lineEnd)
      const lines = block.length === 0 ? [''] : block.split('\n')
      const numbered = lines.map((line, index) => `${index + 1}. ${line}`).join('\n')
      const newValue = value.slice(0, lineStart) + numbered + value.slice(lineEnd)

      if (!hadSelection) {
        const lineIndex = lineIndexWithinBlock(value, lineStart, start)
        const prefixLength = `${lineIndex + 1}. `.length
        const lineText = lines[lineIndex] ?? ''
        const cursor = lineStart + offsetWithinBlock(lines, lineIndex) + prefixLength + lineText.length
        return { value: newValue, ...collapsedCaret(cursor) }
      }

      return {
        value: newValue,
        selectionStart: lineStart,
        selectionEnd: lineStart + numbered.length,
      }
    case 'link': {
      const selected = value.slice(start, end)
      const label = selected || 'text'
      const inserted = `[${label}](url)`
      const newValue = value.slice(0, start) + inserted + value.slice(end)

      if (hadSelection) {
        const urlStart = start + label.length + 3
        return { value: newValue, selectionStart: urlStart, selectionEnd: urlStart + 3 }
      }

      const urlStart = start + label.length + 3
      return { value: newValue, ...collapsedCaret(urlStart) }
    }
    case 'codeBlock': {
      if (hadSelection) {
        return wrapSelection(value, start, end, '```\n', '\n```', 'code')
      }

      const inserted = '```\n\n```'
      const newValue = value.slice(0, start) + inserted + value.slice(end)
      return { value: newValue, ...collapsedCaret(start + 4) }
    }
    case 'hr': {
      const insertion = '\n\n---\n\n'
      const newValue = value.slice(0, end) + insertion + value.slice(end)
      return { value: newValue, ...collapsedCaret(end + insertion.length) }
    }
    default:
      return { value, selectionStart: start, selectionEnd: end }
  }
}

export function matchMarkdownShortcut(event: KeyboardEvent): MarkdownAction | null {
  const mod = event.metaKey || event.ctrlKey
  if (!mod) return null

  const key = event.key.toLowerCase()
  if (key === 'b' && !event.shiftKey) return 'bold'
  if (key === 'i' && !event.shiftKey) return 'italic'
  if (key === 'k' && !event.shiftKey) return 'link'
  if (key === 'e' && !event.shiftKey) return 'code'
  if (key === 'x' && event.shiftKey) return 'strike'
  if (key === '7' && event.shiftKey) return 'ol'
  if (key === '8' && event.shiftKey) return 'ul'

  return null
}
