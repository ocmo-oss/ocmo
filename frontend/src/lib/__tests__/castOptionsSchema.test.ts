import { describe, expect, it } from 'vitest'
import {
  castOptionEnumValues,
  castOptionFieldLabel,
  castOptionPlaceholder,
  formatCastOptionDefault,
} from '../castOptionsSchema'

describe('castOptionsSchema', () => {
  it('uses title when present', () => {
    expect(castOptionFieldLabel('indent', { title: 'Indent' })).toBe('Indent')
  })

  it('extracts enum values from anyOf', () => {
    expect(
      castOptionEnumValues({
        anyOf: [
          { type: 'string', enum: ['block', 'flow', 'auto'] },
          { type: 'null' },
        ],
      }),
    ).toEqual(['block', 'flow', 'auto'])
  })

  it('prefers default for placeholder', () => {
    expect(castOptionPlaceholder({ default: '_', examples: ['.'] })).toBe('_')
  })

  it('formats null default for display', () => {
    expect(formatCastOptionDefault({ default: null })).toBe('null (auto)')
  })
})
