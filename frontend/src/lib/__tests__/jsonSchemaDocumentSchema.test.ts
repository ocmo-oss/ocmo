import { describe, expect, it } from 'vitest'
import {
  subschemaKeywordsForInstanceType,
} from '../jsonSchemaDocumentSchema'
import { JSON_SCHEMA_ROOT_SNIPPET_BODY } from '../yamlCompletion/jsonSchemaCompletion'

describe('subschemaKeywordsForInstanceType', () => {
  it('offers only type/title/description before type is set', () => {
    const keys = Object.keys(subschemaKeywordsForInstanceType(null))
    expect(keys).toEqual(['type', 'title', 'description'])
  })

  it('offers string keywords for string properties', () => {
    const keys = Object.keys(subschemaKeywordsForInstanceType('string'))
    expect(keys).toContain('pattern')
    expect(keys).toContain('format')
    expect(keys).not.toContain('properties')
    expect(keys).not.toContain('items')
  })

  it('offers object keywords for object properties', () => {
    const keys = Object.keys(subschemaKeywordsForInstanceType('object'))
    expect(keys).toContain('properties')
    expect(keys).toContain('required')
    expect(keys).not.toContain('pattern')
  })
})

describe('JSON_SCHEMA_ROOT_SNIPPET_BODY', () => {
  it('includes the draft 2020-12 base structure', () => {
    expect(JSON_SCHEMA_ROOT_SNIPPET_BODY).toContain('$schema: https://json-schema.org/draft/2020-12/schema')
    expect(JSON_SCHEMA_ROOT_SNIPPET_BODY).toContain('type: object')
    expect(JSON_SCHEMA_ROOT_SNIPPET_BODY).toContain('properties: {}')
  })
})
