import { useRef } from 'react'
import clsx from 'clsx'
import stitchData from '../../lib/vyshyvanka/stitch-data.json'
import { usePatternEmbroidery } from '../../lib/vyshyvanka/usePatternEmbroidery'
import type { StitchData } from '../../lib/vyshyvanka/types'
import '../../lib/vyshyvanka/vyshyvanka.css'

const data = stitchData as StitchData

interface VyshyvankaPatternBandProps {
  active: boolean
  className?: string
}

export function VyshyvankaPatternBand({ active, className }: VyshyvankaPatternBandProps) {
  const bandRef = useRef<HTMLElement>(null)
  const { canvasRef } = usePatternEmbroidery(bandRef, data, { active })

  return (
    <article
      ref={bandRef}
      className={clsx(
        'vyshyvanka-band vyshyvanka-band--pattern-only vyshyvanka-band--on-elevated',
        className,
      )}
      aria-hidden={!active}
    >
      <canvas ref={canvasRef} className="vyshyvanka-band__canvas" aria-hidden="true" />
      <div className="vyshyvanka-band__pattern vyshyvanka-band__pattern--fill" aria-hidden="true" />
      <div className="vyshyvanka-band__edge-blur vyshyvanka-band__edge-blur--top" aria-hidden="true" />
      <div className="vyshyvanka-band__edge-blur vyshyvanka-band__edge-blur--bottom" aria-hidden="true" />
    </article>
  )
}
