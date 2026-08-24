import type { ReactNode } from 'react'
import type { AuditTimelineEntry } from '../../api/types'
import { TagBadge, VersionBadge } from '../../lib/itemBadges'

function parseSubresources(
  subresourceType?: string | null,
  subresource?: string | null,
): Record<string, string> {
  if (!subresource) return {}
  const types = (subresourceType ?? '').split(',')
  const values = subresource.split(',')
  const parsed: Record<string, string> = {}
  values.forEach((value, index) => {
    const kind = types[index]?.trim()
    if (kind) parsed[kind] = value
  })
  return parsed
}

interface PropagationAuditTarget {
  path: string
  version: number
}

interface PropagationAuditPayload {
  trigger?: string
  trigger_tag?: string
  targets?: PropagationAuditTarget[]
  unchanged?: string[]
}

function parsePropagationPayload(subresource?: string | null): PropagationAuditPayload | null {
  if (!subresource) return null
  try {
    const data = JSON.parse(subresource) as PropagationAuditPayload
    return data && typeof data === 'object' ? data : { trigger: subresource }
  } catch {
    return { trigger: subresource }
  }
}

function renderPropagationTargets(targets: PropagationAuditTarget[]) {
  return targets.map((target, index) => (
    <span key={`${target.path}@${target.version}`}>
      {index > 0 && ', '}
      <TimelinePath path={target.path} />@<VersionBadge version={target.version} />
    </span>
  ))
}

function renderPropagationPaths(paths: string[]) {
  return paths.map((path, index) => (
    <span key={path}>
      {index > 0 && ', '}
      <TimelinePath path={path} />
    </span>
  ))
}

function TimelineActor({ entry }: { entry: AuditTimelineEntry }) {
  const label = entry.auth_email || entry.auth_id || 'Unknown'
  const prefix = entry.auth_type === 'resolver' ? 'Resolver' : 'User'
  return (
    <span className="font-semibold text-gray-900 dark:text-gray-100">
      {prefix} {label}
    </span>
  )
}

function TimelinePath({ path }: { path: string }) {
  return (
    <span className="font-mono text-[11px] text-gray-600 dark:text-gray-400">
      {path}
    </span>
  )
}

function itemKind(objectType?: string | null): string {
  return objectType ?? 'item'
}

export function AuditTimelineMessage({ entry }: { entry: AuditTimelineEntry }) {
  const subresources = parseSubresources(entry.subresource_type, entry.subresource)
  const kind = itemKind(entry.object_type)
  const operation = entry.operation ?? ''
  const tag = subresources.tag ?? (entry.subresource_type === 'tag' ? entry.subresource : null)
  const version = entry.object_version

  const actor = <TimelineActor entry={entry} />

  let content: ReactNode

  switch (operation) {
    case 'Create item':
      content = version != null
        ? <>created {kind} {entry.object_id && <TimelinePath path={entry.object_id} />} <VersionBadge version={version} /></>
        : <>created {kind} {entry.object_id && <TimelinePath path={entry.object_id} />}</>
      break
    case 'Update item':
      content = version != null
        ? <>created new version of {kind} <VersionBadge version={version} /></>
        : <>updated {kind}</>
      break
    case 'Delete item':
      content = version != null
        ? <>deleted <VersionBadge version={version} /> of {kind}</>
        : <>deleted {kind} {entry.object_id && <TimelinePath path={entry.object_id} />}</>
      break
    case 'Set tag':
      content = tag && version != null
        ? <>set tag <TagBadge name={tag} /> to <VersionBadge version={version} /></>
        : tag
          ? <>set tag <TagBadge name={tag} /></>
          : <>set a tag on {kind}</>
      break
    case 'Delete tag':
      content = tag && version != null
        ? <>removed tag <TagBadge name={tag} /> from <VersionBadge version={version} /></>
        : tag
          ? <>removed tag <TagBadge name={tag} /></>
          : <>removed a tag from {kind}</>
      break
    case 'Update description':
      content = <>updated description of {kind}</>
      break
    case 'Move item': {
      const destination = subresources.path ?? entry.subresource
      content = destination
        ? <>moved {kind} to <TimelinePath path={destination} /></>
        : <>moved {kind}</>
      break
    }
    case 'Copy item': {
      const destination = subresources.path
      const copyTag = subresources.tag
      content = destination && copyTag
        ? <>copied {kind} to <TimelinePath path={destination} /> (tag <TagBadge name={copyTag} />)</>
        : destination
          ? <>copied {kind} to <TimelinePath path={destination} /></>
          : <>copied {kind}</>
      break
    }
    case 'Propagate config': {
      const data = parsePropagationPayload(entry.subresource)
      const trigger = data?.trigger ?? ''
      const triggerTag = data?.trigger_tag ?? ''
      const updated = data?.targets ?? []
      const unchanged = data?.unchanged ?? []

      if (trigger === 'manual') {
        content = version != null
          ? updated.length > 0
            ? <>manually propagated <VersionBadge version={version} /> to {renderPropagationTargets(updated)}</>
            : unchanged.length > 0
              ? <>manually propagated <VersionBadge version={version} />; all targets already matched ({renderPropagationPaths(unchanged)})</>
              : <>manually propagated <VersionBadge version={version} /></>
          : <>manually propagated {kind}</>
      } else if (trigger === 'tag' && triggerTag) {
        content = version != null
          ? updated.length > 0
            ? <>propagated by setting tag <TagBadge name={triggerTag} /> to <VersionBadge version={version} />, creating {renderPropagationTargets(updated)}</>
            : unchanged.length > 0
              ? <>propagated by setting tag <TagBadge name={triggerTag} /> to <VersionBadge version={version} />; all targets already matched ({renderPropagationPaths(unchanged)})</>
              : <>propagated by setting tag <TagBadge name={triggerTag} /> to <VersionBadge version={version} /></>
          : <>propagated by setting tag <TagBadge name={triggerTag} /></>
      } else if (version != null) {
        content = <>propagated <VersionBadge version={version} /> of {kind}</>
      } else {
        content = <>propagated {kind}</>
      }
      break
    }
    case 'Promote stable tag': {
      const promotedTag = tag ?? 'stable'
      content = <>promoted tag <TagBadge name={promotedTag} /> on {kind}</>
      break
    }
    case 'Rotate token': {
      const token = subresources.token ?? entry.subresource
      content = token ? <>rotated resolver token {token}</> : <>rotated resolver token</>
      break
    }
    case 'Create lock':
      content = <>created lock on {entry.object_id && <TimelinePath path={entry.object_id} />}</>
      break
    case 'Update lock':
      content = <>updated lock on {entry.object_id && <TimelinePath path={entry.object_id} />}</>
      break
    case 'Delete lock':
      content = <>deleted lock on {entry.object_id && <TimelinePath path={entry.object_id} />}</>
      break
    default:
      content = <>{operation.toLowerCase()}</>
      break
  }

  if (!operation) {
    return <span>{entry.message}</span>
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-x-1 gap-y-0.5">
      {actor} {content}
    </span>
  )
}
