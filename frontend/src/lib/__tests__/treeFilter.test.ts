import { describe, expect, it } from 'vitest'
import { isTreeNodeVisible } from '../treeFilter'

describe('isTreeNodeVisible', () => {
  it('shows all nodes when search is inactive and there are no matches', () => {
    expect(isTreeNodeVisible('app/cfg', new Set())).toBe(true)
  })

  it('hides all nodes when search is active with zero matches', () => {
    expect(isTreeNodeVisible('app/cfg', new Set(), true)).toBe(false)
  })

  it('shows matching nodes when search is active', () => {
    const matches = new Set(['app/cfg'])
    expect(isTreeNodeVisible('app/cfg', matches, true)).toBe(true)
    expect(isTreeNodeVisible('other/cfg', matches, true)).toBe(false)
  })
})
