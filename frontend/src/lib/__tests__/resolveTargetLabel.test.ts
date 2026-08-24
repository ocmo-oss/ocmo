import { describe, expect, it } from 'vitest'
import { resolveActionLabel, resolveTargetLabel, emptyResolveArtifactsMessage } from '../resolveTargetLabel'

describe('resolveTargetLabel', () => {
  it('returns draft when editor is dirty', () => {
    expect(resolveTargetLabel(true, '5')).toBe('draft')
    expect(resolveTargetLabel(true)).toBe('draft')
  })

  it('returns version label for numeric refs', () => {
    expect(resolveTargetLabel(false, '8')).toBe('v8')
  })

  it('returns tag name for non-numeric refs', () => {
    expect(resolveTargetLabel(false, 'stable')).toBe('stable')
  })

  it('returns latest when unpinned', () => {
    expect(resolveTargetLabel(false)).toBe('latest')
    expect(resolveTargetLabel(false, 'latest')).toBe('latest')
  })
})

describe('resolveActionLabel', () => {
  it('builds action labels', () => {
    expect(resolveActionLabel(false, '3')).toBe('Resolve v3')
    expect(resolveActionLabel(false, 'stable')).toBe('Resolve stable')
    expect(resolveActionLabel(true)).toBe('Resolve draft')
    expect(resolveActionLabel(false, '3', { markStable: true })).toBe('Resolve v3 & mark stable')
  })
})

describe('emptyResolveArtifactsMessage', () => {
  it('describes empty folder resolve', () => {
    expect(emptyResolveArtifactsMessage({ mode: 'folder' }))
      .toBe('No resolvable configs found in this folder.')
  })

  it('describes folder resolve with missing tags skipped', () => {
    expect(emptyResolveArtifactsMessage({
      mode: 'folder',
      ignoreMissingTags: true,
      versionRef: 'stable',
    })).toContain('No configs in this folder matched version "stable"')
  })

  it('describes empty config resolve', () => {
    expect(emptyResolveArtifactsMessage({ mode: 'config' }))
      .toBe('Resolve completed with no output artifacts.')
  })
})
