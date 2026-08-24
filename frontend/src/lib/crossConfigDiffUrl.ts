export interface CrossConfigDiffUrlState {
  fromPath: string
  toPath: string
  fromRef: string
  toRef: string
  reveal: boolean
}

export function parseCrossConfigDiffSearchParams(
  params: URLSearchParams,
): CrossConfigDiffUrlState {
  return {
    fromPath: params.get('from') ?? '',
    toPath: params.get('to') ?? '',
    fromRef: params.get('from_ref') ?? 'latest',
    toRef: params.get('to_ref') ?? 'latest',
    reveal: params.get('reveal') === '1' || params.get('reveal') === 'true',
  }
}

export function buildCrossConfigDiffSearchParams(state: {
  fromPath: string
  toPath: string
  fromRef: string
  toRef: string
  reveal: boolean
}): URLSearchParams {
  const params = new URLSearchParams()
  params.set('from', state.fromPath)
  params.set('to', state.toPath)
  if (state.fromRef !== 'latest') params.set('from_ref', state.fromRef)
  if (state.toRef !== 'latest') params.set('to_ref', state.toRef)
  if (state.reveal) params.set('reveal', '1')
  return params
}

export function crossConfigDiffSearchParamsEqual(
  left: URLSearchParams,
  right: URLSearchParams,
): boolean {
  return left.toString() === right.toString()
}
