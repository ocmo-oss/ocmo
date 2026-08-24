export type StitchPoint = [number, number]

export interface StitchData {
  cell: number
  w: number
  h: number
  rows: number
  cols: number
  pts: StitchPoint[]
}

export type CellKind =
  | 'linen'
  | 'stitch'
  | 'border'
  | 'message'
  | 'accent-top'
  | 'accent-bottom'
  | 'hem-dash'

export interface BandCell {
  x: number
  y: number
  kind: CellKind
  col?: number
  t?: number
}

export interface BandColors {
  linen: string
  stitch: string
  border: string
  message: string
  accentTop: string
  accentBottom: string
}
