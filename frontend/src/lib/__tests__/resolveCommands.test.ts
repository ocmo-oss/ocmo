import { describe, expect, it } from 'vitest'
import {
  buildResolveCliCommand,
  buildResolveCurlCommand,
  buildResolveSdkCommand,
  encodeResolvePath,
} from '../resolveCommands'

const baseConfig = {
  namespace: 'prod',
  path: 'app/web',
  noCreds: true,
  cast: 'json',
  castOptions: { indent: '2' },
  dynamicParams: { env: 'prod' },
  apiBase: 'http://localhost:8000',
} as const

describe('encodeResolvePath', () => {
  it('encodes resolver scope root segments', () => {
    expect(encodeResolvePath('.')).toBe('@')
    expect(encodeResolvePath('app/./web')).toBe('app/@/web')
  })
})

describe('buildResolveCurlCommand', () => {
  it('builds a GET resolve curl command with query params', () => {
    expect(buildResolveCurlCommand({
      ...baseConfig,
      versionRef: 'stable',
    })).toBe(
      "curl -sS -H 'Authorization: Bearer $OCMO_TOKEN' "
      + "'http://localhost:8000/api/v1/ns/prod/~resolve/app/web?version=stable&no-creds=true&cast=json&param_env=prod&cast_option_indent=2'",
    )
  })

  it('builds a POST draft resolve curl command', () => {
    const command = buildResolveCurlCommand({
      ...baseConfig,
      isDraft: true,
      versionRef: 'stable',
    })
    expect(command).toContain('-X POST')
    expect(command).toContain('~resolve-draft/app/web')
    expect(command).toContain('--data-binary @draft.yaml')
    expect(command).not.toContain('version=stable')
  })
})

describe('buildResolveCliCommand', () => {
  it('builds a resolve command with version suffix and options', () => {
    expect(buildResolveCliCommand({
      ...baseConfig,
      versionRef: 'stable',
    })).toBe(
      "ocmo -n prod resolve app/web@stable --cast json --param env=prod --cast-option indent=2\n"
      + '# CLI does not expose: no-creds (use curl or SDK)',
    )
  })

  it('builds a folder resolve command with trailing slash', () => {
    expect(buildResolveCliCommand({
      ...baseConfig,
      path: 'app',
      mode: 'folder',
      cast: '',
      castOptions: {},
      dynamicParams: {},
      noCreds: false,
      ignoreConfigsWithMissingTags: true,
    })).toBe(
      'ocmo -n prod resolve app/\n'
      + '# CLI does not expose: ignore-configs-with-missing-tags (use curl or SDK)',
    )
  })

  it('builds a draft resolve command', () => {
    expect(buildResolveCliCommand({
      ...baseConfig,
      isDraft: true,
    })).toBe(
      "ocmo -n prod resolve draft app/web -f draft.yaml --cast json --param env=prod --cast-option indent=2\n"
      + '# CLI does not expose: no-creds (use curl or SDK)',
    )
  })
})

describe('buildResolveSdkCommand', () => {
  it('builds a resolve SDK snippet', () => {
    const command = buildResolveSdkCommand({
      ...baseConfig,
      versionRef: 'stable',
    })
    expect(command).toContain('client.ns("prod").resolve(')
    expect(command).toContain('version="stable",')
    expect(command).toContain('cast="json",')
    expect(command).toContain('no_creds=True,')
    expect(command).toContain('"env": "prod"')
    expect(command).toContain('"indent": "2"')
  })

  it('builds a draft SDK snippet', () => {
    const command = buildResolveSdkCommand({
      ...baseConfig,
      isDraft: true,
    })
    expect(command).toContain('resolve_draft_config(')
    expect(command).toContain('Path("draft.yaml").read_text()')
    expect(command).not.toContain('version=')
  })
})
