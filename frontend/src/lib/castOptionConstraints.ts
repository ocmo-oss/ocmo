import type { JsonSchemaProperty } from './castOptionsSchema'

export interface CastOptionFieldState {
  disabled: boolean
  reason?: string
}

function effectiveValue(
  values: Record<string, string | boolean>,
  key: string,
  prop?: JsonSchemaProperty,
): string | boolean | undefined {
  if (key in values) return values[key]
  if (prop?.default !== undefined) return prop.default as string | boolean
  return undefined
}

function matchesEnabledWhen(
  values: Record<string, string | boolean>,
  properties: Record<string, JsonSchemaProperty>,
  enabledWhen?: Record<string, string>,
): boolean {
  if (!enabledWhen) return true
  return Object.entries(enabledWhen).every(([key, expected]) => {
    const actual = effectiveValue(values, key, properties[key])
    return String(actual ?? '') === expected
  })
}

export function getCastOptionFieldState(
  field: string,
  prop: JsonSchemaProperty,
  properties: Record<string, JsonSchemaProperty>,
  values: Record<string, string | boolean>,
): CastOptionFieldState {
  const incompatibleWith = prop['x-ocmo-incompatible-with'] as string[] | undefined
  if (incompatibleWith?.some(other => effectiveValue(values, other, properties[other]) === true)) {
    const blocker = incompatibleWith.find(other => effectiveValue(values, other, properties[other]) === true)
    const blockerLabel = blocker ? properties[blocker]?.title ?? blocker.replace(/_/g, ' ') : 'another option'
    return { disabled: true, reason: `Incompatible with ${blockerLabel}` }
  }

  const enabledWhen = prop['x-ocmo-enabled-when'] as Record<string, string> | undefined
  if (!matchesEnabledWhen(values, properties, enabledWhen)) {
    const requirement = enabledWhen
      ? Object.entries(enabledWhen).map(([key, value]) => `${key}=${value}`).join(', ')
      : ''
    return { disabled: true, reason: requirement ? `Only applies when ${requirement}` : undefined }
  }

  return { disabled: false }
}

export function applyCastOptionChange(
  key: string,
  value: string | boolean,
  properties: Record<string, JsonSchemaProperty>,
  values: Record<string, string | boolean>,
): Record<string, string | boolean> {
  const next = { ...values, [key]: value }
  const prop = properties[key]
  const incompatibleWith = prop?.['x-ocmo-incompatible-with'] as string[] | undefined

  if (value === true && incompatibleWith) {
    for (const other of incompatibleWith) {
      delete next[other]
    }
  }

  return next
}
