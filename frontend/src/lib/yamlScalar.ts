const YAML_RESERVED = /^(?:~|null|true|false|yes|no|on|off)$/i
const YAML_NUMBER = /^[-+]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/

export type YamlScalarKind = 'string' | 'number' | 'integer' | 'boolean'

export function yamlScalarKindFromSchema(schema: Record<string, unknown> | null | undefined): YamlScalarKind {
  if (!schema) return 'string'
  const type = schema.type
  if (type === 'boolean') return 'boolean'
  if (type === 'integer') return 'integer'
  if (type === 'number') return 'number'
  if (Array.isArray(type)) {
    if (type.includes('boolean')) return 'boolean'
    if (type.includes('integer')) return 'integer'
    if (type.includes('number')) return 'number'
  }
  return 'string'
}

/** True when a plain (unquoted) YAML scalar would be parsed incorrectly. */
export function needsYamlQuoting(value: string): boolean {
  if (value === '') return true
  if (value !== value.trim()) return true
  if (YAML_RESERVED.test(value)) return true
  if (YAML_NUMBER.test(value)) return true
  if (/^[-?:,\[\]{}#&*!|>'"%@`]/.test(value)) return true
  if (/[: \t]$/.test(value)) return true
  if (/[\n\r\t\u0000-\u001F\u007F]/.test(value)) return true
  if (/:\s/.test(value)) return true
  if (/:\S/.test(value) && !/^\w[\w+.-]*:\/\//.test(value)) return true
  if (/[#&*!|>`{}[\]'"]/.test(value)) return true
  return false
}

function escapeYamlDoubleQuoted(value: string): string {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t')
}

/** Format a string for insertion as a YAML scalar value. */
export function formatYamlScalar(value: string): string {
  if (!needsYamlQuoting(value)) return value
  return `"${escapeYamlDoubleQuoted(value)}"`
}

export function formatYamlScalarValue(
  value: unknown,
  kind: YamlScalarKind = 'string',
): string {
  if (kind === 'boolean') {
    if (typeof value === 'boolean') return value ? 'true' : 'false'
    if (value === 'true' || value === 'false') return String(value)
  }
  if (kind === 'integer' || kind === 'number') {
    if (typeof value === 'number') return String(value)
    if (typeof value === 'string' && YAML_NUMBER.test(value)) return value
  }
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') return String(value)
  if (value === null || value === undefined) return 'null'
  return formatYamlScalar(String(value))
}

/** Snippet-safe YAML scalar: literals when quoting/snippet chars are required. */
export function formatYamlScalarSnippet(
  tab: number,
  rawValue: string,
  kind: YamlScalarKind = 'string',
): { text: string; nextTab: number } {
  if (kind !== 'string') {
    if (/[\\$}]/.test(rawValue)) {
      return { text: rawValue, nextTab: tab }
    }
    return { text: `\${${tab}:${rawValue}}`, nextTab: tab + 1 }
  }
  if (needsYamlQuoting(rawValue) || /[\\$}]/.test(rawValue)) {
    return { text: formatYamlScalar(rawValue), nextTab: tab }
  }
  return { text: `\${${tab}:${rawValue}}`, nextTab: tab + 1 }
}
