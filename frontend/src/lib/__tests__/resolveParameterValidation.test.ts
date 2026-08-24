import { describe, expect, it } from 'vitest'
import { validateDynamicParamValue } from '../resolveParameterValidation'

describe('validateDynamicParamValue', () => {
  it('allows incomplete bool literals while typing', () => {
    expect(validateDynamicParamValue('f', ['bool'])).toBeNull()
    expect(validateDynamicParamValue('fa', ['bool'])).toBeNull()
    expect(validateDynamicParamValue('false', ['bool'])).toBeNull()
    expect(validateDynamicParamValue('true', ['bool'])).toBeNull()
  })

  it('rejects invalid bool values', () => {
    expect(validateDynamicParamValue('fx', ['bool'])).toMatch(/Cannot cast/)
    expect(validateDynamicParamValue('maybe', ['bool'])).toMatch(/Cannot cast/)
  })

  it('allows partial numeric input', () => {
    expect(validateDynamicParamValue('-', ['int'])).toBeNull()
    expect(validateDynamicParamValue('12', ['int'])).toBeNull()
    expect(validateDynamicParamValue('1.', ['float'])).toBeNull()
    expect(validateDynamicParamValue('.5', ['float'])).toBeNull()
  })

  it('rejects invalid numeric input', () => {
    expect(validateDynamicParamValue('12x', ['int'])).toMatch(/Cannot cast/)
    expect(validateDynamicParamValue('1.2.3', ['float'])).toMatch(/Cannot cast/)
  })

  it('ignores non-coercing transformers', () => {
    expect(validateDynamicParamValue('anything', ['lower', 'trim'])).toBeNull()
  })
})
