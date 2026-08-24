import type { BandCell, BandColors, CellKind, StitchData } from './types'

export interface EmbroideryTiming {
  groupStepMs: number
  slotStepMs: number
}

export const NOT_FOUND_TIMING: EmbroideryTiming = { groupStepMs: 25, slotStepMs: 1 }
export const RESOLVE_TIMING: EmbroideryTiming = { groupStepMs: 12, slotStepMs: 1 }

const BORDER_W = 3

const REGION_PATTERN = [
  'left', 'left', 'right', 'center', 'right', 'right',
  'left', 'center', 'right', 'left', 'right', 'center',
  'right', 'left', 'left', 'center', 'right', 'right', 'center', 'left',
] as const

function mulberry32(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function shuffleSeeded<T>(items: T[], seed: number): T[] {
  const arr = [...items]
  const rand = mulberry32(seed)
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rand() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr
}

function stitchRegion(col: number, maxCol: number): 'left' | 'center' | 'right' {
  const third = (maxCol + 1) / 3
  if (col < third) return 'left'
  if (col < third * 2) return 'center'
  return 'right'
}

function embroideryOrder(cells: BandCell[], group: number): BandCell[] {
  if (!cells.length) return []

  const maxCol = Math.max(...cells.map((c) => c.col ?? 0))
  const buckets: Record<'left' | 'center' | 'right', BandCell[]> = {
    left: [],
    center: [],
    right: [],
  }
  for (const cell of cells) {
    buckets[stitchRegion(cell.col ?? 0, maxCol)].push(cell)
  }

  shuffleSeeded(buckets.left, group * 3 + 11)
  shuffleSeeded(buckets.center, group * 3 + 29)
  shuffleSeeded(buckets.right, group * 3 + 47)

  const ordered: BandCell[] = []
  let pi = 0
  while (ordered.length < cells.length) {
    let region = REGION_PATTERN[pi % REGION_PATTERN.length]
    pi += 1
    if (!buckets[region].length) {
      if (buckets.left.length) region = 'left'
      else if (buckets.right.length) region = 'right'
      else region = 'center'
    }
    const next = buckets[region].shift()
    if (next) ordered.push(next)
  }

  return ordered
}

export function scheduleCells(
  cells: BandCell[],
  cellSize: number,
  phaseMs = 0,
  timing: EmbroideryTiming = NOT_FOUND_TIMING,
): BandCell[] {
  const bandMap = new Map<number, BandCell[]>()
  for (const item of cells) {
    const screenRow = Math.floor(item.y / cellSize)
    const group = Math.floor(screenRow / 3)
    const list = bandMap.get(group) ?? []
    list.push({
      ...item,
      col: Math.floor(item.x / cellSize),
    })
    bandMap.set(group, list)
  }

  const schedule: BandCell[] = []
  for (const group of [...bandMap.keys()].sort((a, b) => a - b)) {
    const ordered = embroideryOrder(bandMap.get(group) ?? [], group)
    ordered.forEach((entry, slot) => {
      schedule.push({
        ...entry,
        t: phaseMs + group * timing.groupStepMs + slot * timing.slotStepMs,
      })
    })
  }

  schedule.sort((a, b) => (a.t ?? 0) - (b.t ?? 0))
  return schedule
}

export function readBandColors(root: HTMLElement): BandColors {
  const style = getComputedStyle(root)
  return {
    linen: style.getPropertyValue('--vy-linen').trim() || '#2a7db5',
    stitch: style.getPropertyValue('--vy-stitch').trim() || '#ffffff',
    border: style.getPropertyValue('--vy-border').trim() || '#1e40af',
    message: style.getPropertyValue('--vy-message-bg').trim() || '#f6f7f9',
    accentTop: style.getPropertyValue('--vy-accent-top').trim() || '#1e40af',
    accentBottom: style.getPropertyValue('--vy-accent-bottom').trim() || '#2563eb',
  }
}

export interface BandLayout {
  width: number
  topH: number
  msgTop: number
  msgH: number
  bottomTop: number
  bottomH: number
  totalH: number
}

export function buildBandCells(
  data: StitchData,
  layout: BandLayout,
  messageFontSize: number,
): BandCell[] {
  const { cell, w: tileW, h: tileH, pts } = data
  const stitchSet = new Set(pts.map(([x, y]) => `${x},${y}`))
  const { width: w, topH, msgTop, msgH, bottomTop, bottomH, totalH } = layout
  const innerW = w - BORDER_W * 2
  const cells: BandCell[] = []

  const push = (x: number, y: number, kind: CellKind) => {
    cells.push({ x, y, kind })
  }

  const addHemDashes = (y: number) => {
    const inset = 16
    const dash = 6
    const gap = 6
    const rowY = Math.round(y)
    for (let x = inset; x < w - inset; x += dash + gap) {
      for (let dx = 0; dx < dash; dx += cell) {
        if (x + dx >= w - inset) break
        push(x + dx, rowY, 'hem-dash')
      }
    }
  }

  const addPatternSection = (sectionTop: number, sectionH: number) => {
    for (let ty = 0; ty * tileH < sectionH; ty += 1) {
      for (let py = 0; py < tileH; py += cell) {
        const gy = sectionTop + ty * tileH + py
        if (gy >= sectionTop + sectionH) break
        for (let px = 0; px < tileW; px += cell) {
          if (px >= innerW) continue
          const x = BORDER_W + px
          const key = `${px},${py}`
          push(x, gy, 'linen')
          if (stitchSet.has(key)) push(x, gy, 'stitch')
        }
      }
    }
  }

  for (let y = 0; y < totalH; y += cell) {
    for (let bx = 0; bx < BORDER_W; bx += 1) push(bx, y, 'border')
    for (let bx = w - BORDER_W; bx < w; bx += 1) push(bx, y, 'border')
  }

  addPatternSection(0, topH)

  for (let y = msgTop; y < msgTop + msgH; y += cell) {
    for (let x = BORDER_W; x < w - BORDER_W; x += cell) {
      const relY = y - msgTop
      if (relY < cell) push(x, y, 'accent-top')
      else if (relY >= msgH - cell) push(x, y, 'accent-bottom')
      else push(x, y, 'message')
    }
  }

  const hemInset = messageFontSize * 0.65
  addHemDashes(msgTop + hemInset)
  addHemDashes(msgTop + msgH - hemInset - cell)

  addPatternSection(bottomTop, bottomH)

  return cells
}

export function buildPatternOnlyCells(
  data: StitchData,
  width: number,
  height: number,
): BandCell[] {
  const { cell, w: tileW, h: tileH, pts } = data
  const stitchSet = new Set(pts.map(([x, y]) => `${x},${y}`))
  const innerW = width - BORDER_W * 2
  const cells: BandCell[] = []

  const push = (x: number, y: number, kind: CellKind) => {
    cells.push({ x, y, kind })
  }

  for (let y = 0; y < height; y += cell) {
    for (let bx = 0; bx < BORDER_W; bx += 1) push(bx, y, 'border')
    for (let bx = width - BORDER_W; bx < width; bx += 1) push(bx, y, 'border')
  }

  for (let ty = 0; ty * tileH < height; ty += 1) {
    for (let py = 0; py < tileH; py += cell) {
      const gy = ty * tileH + py
      if (gy >= height) break
      for (let px = 0; px < tileW; px += cell) {
        if (px >= innerW) continue
        const x = BORDER_W + px
        const key = `${px},${py}`
        push(x, gy, 'linen')
        if (stitchSet.has(key)) push(x, gy, 'stitch')
      }
    }
  }

  return cells
}

export function drawCell(
  ctx: CanvasRenderingContext2D,
  item: BandCell,
  cell: number,
  colors: BandColors,
) {
  if (item.kind === 'stitch') {
    ctx.fillStyle = colors.stitch
    ctx.fillRect(item.x, item.y, cell, cell)
    return
  }

  const fill: Record<Exclude<CellKind, 'stitch'>, string> = {
    linen: colors.linen,
    border: colors.border,
    message: colors.message,
    'accent-top': colors.accentTop,
    'accent-bottom': colors.accentBottom,
    'hem-dash': colors.accentTop,
  }

  ctx.fillStyle = fill[item.kind]
  ctx.fillRect(item.x, item.y, cell, cell)
}

export const STITCH_MS = 120
