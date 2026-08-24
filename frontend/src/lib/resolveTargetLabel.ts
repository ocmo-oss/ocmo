export function resolveTargetLabel(isDirty: boolean, versionRef?: string): string {
  if (isDirty) return 'draft'
  if (!versionRef || versionRef === 'latest') return 'latest'
  if (/^\d+$/.test(versionRef)) return `v${versionRef}`
  return versionRef
}

export function resolveActionLabel(
  isDirty: boolean,
  versionRef?: string,
  options?: { markStable?: boolean },
): string {
  const base = `Resolve ${resolveTargetLabel(isDirty, versionRef)}`
  return options?.markStable ? `${base} & mark stable` : base
}

export function emptyResolveArtifactsMessage({
  mode = 'config',
  ignoreMissingTags = false,
  versionRef,
}: {
  mode?: 'config' | 'folder'
  ignoreMissingTags?: boolean
  versionRef?: string
} = {}): string {
  if (mode === 'folder') {
    if (ignoreMissingTags) {
      const versionLabel = resolveTargetLabel(false, versionRef)
      return `No configs in this folder matched version "${versionLabel}". Try a different version or disable "Ignore configs with missing tags".`
    }
    return 'No resolvable configs found in this folder.'
  }
  return 'Resolve completed with no output artifacts.'
}
