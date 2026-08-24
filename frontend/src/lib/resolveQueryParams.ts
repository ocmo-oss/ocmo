export function buildResolveQueryParams({
  versionRef,
  noCreds,
  dynamicParams,
  cast,
  markStable,
  castOptions,
  ignoreConfigsWithMissingTags,
}: {
  versionRef?: string
  noCreds: boolean
  dynamicParams: Record<string, string>
  cast?: string
  markStable?: boolean
  castOptions?: Record<string, string | boolean>
  ignoreConfigsWithMissingTags?: boolean
}): Record<string, string | boolean> {
  const params: Record<string, string | boolean> = {
    version: versionRef ?? 'latest',
  }
  if (noCreds) params['no-creds'] = true
  if (markStable) params['mark-stable'] = true
  if (ignoreConfigsWithMissingTags) params['ignore-configs-with-missing-tags'] = true
  if (cast) params.cast = cast
  for (const [k, v] of Object.entries(dynamicParams)) {
    if (v !== '') params[`param_${k}`] = v
  }
  if (castOptions) {
    for (const [k, v] of Object.entries(castOptions)) {
      if (v !== '' && v !== undefined && v !== null) params[`cast_option_${k}`] = String(v)
    }
  }
  return params
}
