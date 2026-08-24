import { buildResolveQueryParams } from './resolveQueryParams'

export interface ResolveCommandConfig {
  namespace: string
  path: string
  mode?: 'config' | 'folder'
  versionRef?: string
  noCreds: boolean
  cast: string
  castOptions: Record<string, string | boolean>
  dynamicParams: Record<string, string>
  ignoreConfigsWithMissingTags?: boolean
  isDraft?: boolean
  apiBase?: string
}

function resolveApiOrigin(apiBase?: string): string {
  if (apiBase) return apiBase.replace(/\/$/, '')
  if (typeof window !== 'undefined') return window.location.origin
  return 'http://localhost:8000'
}

/** Mirror SDK ``_encode_resolve_path``: lone ``.`` segments become ``@`` on the wire. */
export function encodeResolvePath(path: string): string {
  return path
    .split('/')
    .map(segment => (segment === '.' ? '@' : encodeURIComponent(segment)))
    .join('/')
}

function shellQuote(value: string): string {
  if (/^[a-zA-Z0-9_./@=-]+$/.test(value)) return value
  return `'${value.replace(/'/g, `'\\''`)}'`
}

function cliAddress(path: string, mode: 'config' | 'folder', versionRef?: string): string {
  let address = mode === 'folder' && !path.endsWith('/') ? `${path}/` : path
  const version = versionRef ?? 'latest'
  if (version !== 'latest') {
    address += `@${version}`
  }
  return address
}

function buildQueryParams(config: ResolveCommandConfig): Record<string, string | boolean> {
  return buildResolveQueryParams({
    versionRef: config.isDraft ? undefined : config.versionRef,
    noCreds: config.noCreds,
    dynamicParams: config.dynamicParams,
    cast: config.cast,
    castOptions: config.castOptions,
    ignoreConfigsWithMissingTags: config.ignoreConfigsWithMissingTags,
  })
}

function formatQueryString(params: Record<string, string | boolean>): string {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (key === 'version' && value === 'latest') continue
    qs.set(key, String(value))
  }
  return qs.toString()
}

function dynamicParamsDict(config: ResolveCommandConfig): Record<string, string> {
  const params: Record<string, string> = {}
  for (const [key, value] of Object.entries(config.dynamicParams)) {
    if (value !== '') params[key] = value
  }
  return params
}

function castOptionsDict(config: ResolveCommandConfig): Record<string, string> {
  const options: Record<string, string> = {}
  for (const [key, value] of Object.entries(config.castOptions)) {
    if (value !== '' && value !== undefined && value !== null) {
      options[key] = String(value)
    }
  }
  return options
}

function formatPythonString(value: string): string {
  if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value)) return `"${value}"`
  return JSON.stringify(value)
}

function formatPythonDict(data: Record<string, string>): string | null {
  const entries = Object.entries(data)
  if (entries.length === 0) return null
  const lines = entries.map(([key, value]) => `        ${formatPythonString(key)}: ${formatPythonString(value)},`)
  return `{\n${lines.join('\n')}\n    }`
}

export function buildResolveCurlCommand(config: ResolveCommandConfig): string {
  const origin = resolveApiOrigin(config.apiBase)
  const encodedPath = encodeResolvePath(config.path)
  const query = formatQueryString(buildQueryParams(config))
  const querySuffix = query ? `?${query}` : ''

  if (config.isDraft) {
    return [
      `curl -sS -X POST \\`,
      `  -H 'Authorization: Bearer $OCMO_TOKEN' \\`,
      `  -H 'Content-Type: application/yaml' \\`,
      `  --data-binary @draft.yaml \\`,
      `  '${origin}/api/v1/ns/${config.namespace}/~resolve-draft/${encodedPath}${querySuffix}'`,
    ].join('\n')
  }

  return `curl -sS -H 'Authorization: Bearer $OCMO_TOKEN' '${origin}/api/v1/ns/${config.namespace}/~resolve/${encodedPath}${querySuffix}'`
}

export function buildResolveCliCommand(config: ResolveCommandConfig): string {
  const parts = ['ocmo', '-n', shellQuote(config.namespace)]

  if (config.isDraft) {
    parts.push('resolve', 'draft', shellQuote(config.path))
    parts.push('-f', 'draft.yaml')
  } else {
    parts.push('resolve', shellQuote(cliAddress(config.path, config.mode ?? 'config', config.versionRef)))
  }

  if (config.cast) {
    parts.push('--cast', shellQuote(config.cast))
  }

  for (const [key, value] of Object.entries(dynamicParamsDict(config))) {
    parts.push('--param', shellQuote(`${key}=${value}`))
  }

  for (const [key, value] of Object.entries(castOptionsDict(config))) {
    parts.push('--cast-option', shellQuote(`${key}=${value}`))
  }

  const unsupported: string[] = []
  if (config.noCreds) unsupported.push('no-creds')
  if (config.ignoreConfigsWithMissingTags) unsupported.push('ignore-configs-with-missing-tags')

  const command = parts.join(' ')
  if (unsupported.length === 0) return command
  return `${command}\n# CLI does not expose: ${unsupported.join(', ')} (use curl or SDK)`
}

export function buildResolveSdkCommand(config: ResolveCommandConfig): string {
  const lines = [
    'from ocmo import OcmoClient',
    '',
    'client = OcmoClient()',
  ]

  const kwargs: string[] = []

  if (!config.isDraft) {
    const version = config.versionRef ?? 'latest'
    if (version !== 'latest') {
      kwargs.push(`    version=${formatPythonString(version)},`)
    }
  }

  if (config.cast) {
    kwargs.push(`    cast=${formatPythonString(config.cast)},`)
  }

  if (config.noCreds) {
    kwargs.push('    no_creds=True,')
  }

  if (config.ignoreConfigsWithMissingTags) {
    kwargs.push('    ignore_configs_with_missing_tags=True,')
  }

  const params = formatPythonDict(dynamicParamsDict(config))
  if (params) {
    kwargs.push(`    params=${params},`)
  }

  const castOptions = formatPythonDict(castOptionsDict(config))
  if (castOptions) {
    kwargs.push(`    cast_options=${castOptions},`)
  }

  if (config.isDraft) {
    lines.push('from pathlib import Path')
    lines.push('')
    lines.push(`result = client.ns(${formatPythonString(config.namespace)}).resolve_draft_config(`)
    lines.push(`    ${formatPythonString(config.path)},`)
    lines.push('    content=Path("draft.yaml").read_text(),')
    if (kwargs.length > 0) {
      lines.push(...kwargs)
    }
    lines.push(')')
    if (params) {
      lines.push('# Draft dynamic params are sent as query params; use curl for the exact HTTP call.')
    }
    return lines.join('\n')
  }

  lines.push(`result = client.ns(${formatPythonString(config.namespace)}).resolve(`)
  lines.push(`    ${formatPythonString(config.path)},`)
  if (kwargs.length > 0) {
    lines.push(...kwargs)
  }
  lines.push(')')
  lines.push('')
  lines.push('# Access artifacts lazily, e.g. result["app.json"].text')

  return lines.join('\n')
}
