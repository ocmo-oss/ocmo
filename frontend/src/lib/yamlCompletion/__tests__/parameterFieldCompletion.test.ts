import { describe, it, expect } from 'vitest'
import { __testing } from '../yamlSchemaCompletion'
import { textModel, makePosition, monacoStub } from './monacoStub'
import { buildConfigEditorSchema } from '../../configEditorSchema'
import {
  __testingParameterDeclarationCompletion,
  PROJECTED_PARAMETER_SELECTORS,
  shouldSuggestParameterValue,
} from '../ocmoParameterDeclarationCompletion'

const metadataSchema = {
  type: 'object',
  properties: {
    parameters: {
      type: 'object',
      additionalProperties: { $ref: '#/$defs/ConfigParameterSchema' },
    },
  },
  $defs: {
    ConfigParameterSchema: {
      type: 'object',
      properties: {
        type: { type: 'string', enum: ['projected', 'dynamic', 'secret'] },
        value: { description: 'value field' },
        description: { type: 'string' },
        transformers: {
          type: 'array',
          items: { type: 'string', enum: ['lower', 'upper', 'urlencode'] },
        },
      },
      required: ['type', 'value', 'description'],
    },
  },
}

const editorSchema = buildConfigEditorSchema('_ocmo', metadataSchema, {
  type: 'object',
  properties: { foo: { type: 'string' } },
})

const uriOptions = {
  namespace: 'default',
  configPath: 'apps/demo',
  metadataKey: '_ocmo',
}

function labels(items: Array<{ label: unknown }>): string[] {
  return items.map(item => (
    typeof item.label === 'string'
      ? item.label
      : (item.label as { label?: string })?.label ?? String(item.label)
  ))
}

async function getSuggestions(
  yaml: string,
  lineNumber: number,
  column: number,
  paramOptions: { metadataKey: string } | null = { metadataKey: '_ocmo' },
) {
  const model = textModel(yaml)
  const position = makePosition(lineNumber, column)
  const result = __testing.buildYamlCompletionSuggestions(
    monacoStub as never,
    editorSchema,
    model as never,
    position as never,
    uriOptions,
    paramOptions,
  )
  const items = result instanceof Promise ? await result : result
  return items
}

describe('parameter declaration field completion', () => {
  it('suggests parameter property keys on the properly indented child line', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      ',
    ].join('\n')
    const items = await getSuggestions(yaml, 4, 7)
    expect(labels(items)).toEqual(expect.arrayContaining(['type', 'value', 'description', 'transformers']))
  })

  it('does not suggest parameter fields on the parameter name line', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    myparam:',
    ].join('\n')
    const line = yaml.split('\n')[2]
    const items = await getSuggestions(yaml, 3, line.length + 1)
    expect(labels(items)).not.toContain('type')
    expect(labels(items)).not.toContain('value')
  })

  it('does not suggest parameter fields on an unindented line after the parameter name', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '',
    ].join('\n')
    const items = await getSuggestions(yaml, 4, 1)
    expect(labels(items)).not.toContain('type')
    expect(labels(items)).not.toContain('transformers')
  })

  it('suggests missing transformers on a new line after other parameter fields', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    name:',
      '      type: projected',
      '      value: ".Path[-1]"',
      '      description: Last segment of the config path',
      '      ',
    ].join('\n')
    const items = await getSuggestions(yaml, 7, 7)
    expect(labels(items)).toContain('transformers')
    expect(labels(items)).not.toContain('type')
    expect(labels(items)).not.toContain('value')
    expect(labels(items)).not.toContain('description')
  })

  it('suggests missing fields without paramOptions when object path is detectable', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      ',
    ].join('\n')
    const items = await getSuggestions(yaml, 4, 7, null)
    expect(labels(items)).toEqual(expect.arrayContaining(['type', 'value', 'description', 'transformers']))
  })

  it('scopes missing fields to the enclosing parameter when multiple are declared', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    first:',
      '      type: projected',
      '      value: ".Name"',
      '      description: first param',
      '    second:',
      '      type: projected',
      '      value: ".Path"',
      '      description: second param',
      '      ',
    ].join('\n')
    const items = await getSuggestions(yaml, 11, 7)
    expect(labels(items)).toEqual(['transformers'])
  })

  it('suggests transformer enum values inside transformers array', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    config_path:',
      '      type: projected',
      '      value: .Path',
      '      description: Full config path from namespace root',
      '      transformers:',
      '        - urlencode',
      '        - ',
    ].join('\n')
    const line = yaml.split('\n')[8]
    const items = await getSuggestions(yaml, 9, line.length + 1)
    expect(labels(items)).toEqual(expect.arrayContaining(['lower', 'upper']))
    expect(labels(items)).not.toContain('type')
  })

  it('uses distinct snippet tab stops for new parameter map entries', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    ',
    ].join('\n')
    const items = await getSuggestions(yaml, 3, 5)
    const mapEntry = items.find(item => {
      const label = typeof item.label === 'string'
        ? item.label
        : (item.label as { label?: string })?.label
      return label === 'name'
    })
    expect(mapEntry).toBeDefined()
    expect(String(mapEntry?.insertText)).toContain('${1:name}:')
    expect(String(mapEntry?.insertText)).toContain('type: ${2:projected}')
    expect(String(mapEntry?.insertText)).not.toContain('type: ${1:')
  })
})

describe('parameter value completion', () => {
  it('suggests projected selectors when type is projected', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      type: projected',
      '      value: ',
    ].join('\n')
    const line = yaml.split('\n')[4]
    const items = await getSuggestions(yaml, 5, line.length + 1)
    expect(labels(items)).toEqual(expect.arrayContaining(PROJECTED_PARAMETER_SELECTORS.map(s => s.label)))
  })

  it('does not suggest values when type is dynamic', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      type: dynamic',
      '      value: ',
    ].join('\n')
    const line = yaml.split('\n')[4]
    const items = await getSuggestions(yaml, 5, line.length + 1)
    expect(items).toEqual([])
  })

  it('filters projected selectors by typed prefix', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      type: projected',
      '      value: .Ver',
    ].join('\n')
    const line = yaml.split('\n')[4]
    const items = await getSuggestions(yaml, 5, line.length + 1)
    expect(labels(items)).toEqual(['.Version.tag', '.Version.number'])
    expect(labels(items)).not.toContain('.Path')
  })

  it('replaces the full value when accepting a projected selector with suffix text', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    name:',
      '      type: projected',
      '      value: .Name',
    ].join('\n')
    const line = yaml.split('\n')[4]
    const cursorCol = line.indexOf('N') + 2
    const items = await getSuggestions(yaml, 5, cursorCol)
    const nameItem = items.find(item => labels([item])[0] === '.Name')
    expect(nameItem).toBeDefined()
    expect(nameItem?.range).toMatchObject({
      startColumn: line.indexOf('.') + 1,
      endColumn: line.length + 1,
    })
    expect(nameItem?.insertText).toBe('.Name')
  })

  it('does not suggest projected selectors when the value is already complete', async () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    name:',
      '      description: test parameter',
      '      type: projected',
      '      value: .Name',
    ].join('\n')
    const line = yaml.split('\n')[5]
    const items = await getSuggestions(yaml, 6, line.length + 1)
    expect(items).toEqual([])
  })

  it('enables secret value completion when type is secret', () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      type: secret',
      '      value: ',
    ].join('\n')
    const model = textModel(yaml)
    const position = makePosition(5, yaml.split('\n')[4].length + 1)
    const ctx = __testing.completionContext(model as never, position as never)
    expect(shouldSuggestParameterValue(
      model as never,
      position as never,
      ctx,
      '_ocmo',
    )).toBe(true)
  })
})

describe('parameter declaration helpers', () => {
  it('reads parameter type from the declaration block', () => {
    const yaml = [
      '_ocmo:',
      '  parameters:',
      '    param_name:',
      '      type: secret',
      '      value: creds/db',
      '      description: db password',
    ].join('\n')
    const model = textModel(yaml)
    expect(__testingParameterDeclarationCompletion.readOcmoParameterType(
      model as never,
      '_ocmo',
      'param_name',
    )).toBe('secret')
  })

  it('does not treat value as a parameter name key', () => {
    expect(__testingParameterDeclarationCompletion.shouldShowProjectedSelectorSuggestion(
      '.Name',
      '.Name',
      '.Name',
    )).toBe(false)
  })
})
