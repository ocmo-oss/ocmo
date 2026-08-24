const BOOL_LITERALS = ['true', 'false', '1', '0', 'yes', 'no', 'on', 'off'] as const

const INT_PARTIAL = /^-?\d*$/
const INT_COMPLETE = /^-?\d+$/

const FLOAT_PARTIAL = /^-?(?:\d+\.?\d*|\.\d*)$/
const FLOAT_COMPLETE = /^-?(?:\d+\.?\d+|\.\d+)$/

function validateBool(value: string): string | null {
  const normalized = value.trim().toLowerCase()
  if (!normalized) return null
  if ((BOOL_LITERALS as readonly string[]).includes(normalized)) return null
  if (BOOL_LITERALS.some(literal => literal.startsWith(normalized))) return null
  return `Cannot cast ${JSON.stringify(value)} to bool`
}

function validateInt(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  if (!INT_PARTIAL.test(trimmed)) {
    return `Cannot cast ${JSON.stringify(value)} to int`
  }
  if (trimmed === '-' || INT_COMPLETE.test(trimmed)) return null
  return null
}

function validateFloat(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  if (!FLOAT_PARTIAL.test(trimmed)) {
    return `Cannot cast ${JSON.stringify(value)} to float`
  }
  if (trimmed === '-' || trimmed === '.' || trimmed === '-.' || FLOAT_COMPLETE.test(trimmed)) {
    return null
  }
  return null
}

const TRANSFORMER_VALIDATORS: Record<string, (value: string) => string | null> = {
  bool: validateBool,
  int: validateInt,
  float: validateFloat,
}

/** Validate a dynamic resolve parameter value against declared transformers. */
export function validateDynamicParamValue(
  value: string,
  transformers: string[] = [],
): string | null {
  for (const transformer of transformers) {
    const validate = TRANSFORMER_VALIDATORS[transformer]
    if (!validate) continue
    const error = validate(value)
    if (error) return error
  }
  return null
}

export function validateDynamicParams(
  values: Record<string, string>,
  parameters: Record<string, { type?: string; transformers_applied?: string[] }>,
): Record<string, string> {
  const errors: Record<string, string> = {}
  for (const [name, param] of Object.entries(parameters)) {
    if (param.type !== 'dynamic') continue
    const error = validateDynamicParamValue(
      values[name] ?? '',
      param.transformers_applied ?? [],
    )
    if (error) errors[name] = error
  }
  return errors
}
