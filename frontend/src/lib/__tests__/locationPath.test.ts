import { describe, expect, it } from 'vitest'
import {
  buildDestinationPathFromFolder,
  filterTreePathInput,
  isPathUnderPrefix,
  splitTreePathSuffixInput,
  validateRelocationTargetPath,
  validateTreePathCharacters,
} from '../locationPath'

describe('filterTreePathInput', () => {
  it('removes disallowed characters', () => {
    expect(filterTreePathInput('app/cfg@#$')).toBe('app/cfg')
    expect(filterTreePathInput('my item')).toBe('myitem')
  })

  it('strips leading slashes and collapses repeated separators', () => {
    expect(filterTreePathInput('/moved/cfg')).toBe('moved/cfg')
    expect(filterTreePathInput('app//cfg')).toBe('app/cfg')
  })
})

describe('buildDestinationPathFromFolder', () => {
  it('appends the item name under the selected folder', () => {
    expect(buildDestinationPathFromFolder('moved', 'cfg1')).toBe('moved/cfg1')
    expect(buildDestinationPathFromFolder('moved/sub', 'cfg1')).toBe('moved/sub/cfg1')
  })
})

describe('splitTreePathSuffixInput', () => {
  it('splits completed segments from the active tail', () => {
    expect(splitTreePathSuffixInput('folder/item')).toEqual({
      completedSegments: ['folder'],
      currentInput: 'item',
    })
  })

  it('filters invalid characters before splitting', () => {
    expect(splitTreePathSuffixInput('my folder/item')).toEqual({
      completedSegments: ['myfolder'],
      currentInput: 'item',
    })
  })
})

describe('validateTreePathCharacters', () => {
  it('accepts valid paths', () => {
    expect(validateTreePathCharacters('app/cfg_v1')).toBeUndefined()
    expect(validateTreePathCharacters('my-folder.item')).toBeUndefined()
  })

  it('rejects dot segments', () => {
    expect(validateTreePathCharacters('app/../cfg')).toBe(
      "Path segments '.' and '..' are not allowed",
    )
  })
})

describe('isPathUnderPrefix', () => {
  it('detects direct and nested descendants', () => {
    expect(isPathUnderPrefix('configX/configY', 'configX')).toBe(true)
    expect(isPathUnderPrefix('app/sub/item', 'app')).toBe(true)
  })

  it('does not treat sibling paths as descendants', () => {
    expect(isPathUnderPrefix('app/cfg2', 'app/cfg')).toBe(false)
    expect(isPathUnderPrefix('configX-extra', 'configX')).toBe(false)
  })
})

describe('validateRelocationTargetPath', () => {
  it('rejects moving an item under its own path', () => {
    expect(validateRelocationTargetPath('configX', 'configX/configY', 'move')).toBe(
      'Destination cannot be under the source path',
    )
  })

  it('allows copying to a child path', () => {
    expect(validateRelocationTargetPath('configX', 'configX/configY', 'copy')).toBeUndefined()
  })
})
