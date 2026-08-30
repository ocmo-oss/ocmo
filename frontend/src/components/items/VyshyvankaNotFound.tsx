import { useRef } from "react";
import clsx from "clsx";
import stitchData from "../../lib/vyshyvanka/stitch-data.json";
import { useBandEmbroidery } from "../../lib/vyshyvanka/useBandEmbroidery";
import type { StitchData } from "../../lib/vyshyvanka/types";
import "../../lib/vyshyvanka/vyshyvanka.css";

const data = stitchData as StitchData;

function CrossStitchDigit4({ offset }: { offset: number }) {
  const i = (n: number) => offset + n;
  return (
    <div className="vy-glyph" aria-hidden="true">
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(0) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(1) } as React.CSSProperties}
      />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(2) } as React.CSSProperties}
      />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(3) } as React.CSSProperties}
      />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(4) } as React.CSSProperties}
      />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(5) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(6) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(7) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(8) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(9) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(10) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(11) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(12) } as React.CSSProperties}
      />
      <span />
    </div>
  );
}

function CrossStitchDigit0({ offset }: { offset: number }) {
  const i = (n: number) => offset + n;
  return (
    <div className="vy-glyph vy-glyph--zero" aria-hidden="true">
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(0) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(1) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(2) } as React.CSSProperties}
      />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(3) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(4) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(5) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(6) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(7) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(8) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(9) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(10) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(11) } as React.CSSProperties}
      />
      <span />
      <span />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(12) } as React.CSSProperties}
      />
      <span />
      <span
        className="vy-stitch"
        style={{ "--i": i(13) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(14) } as React.CSSProperties}
      />
      <span
        className="vy-stitch"
        style={{ "--i": i(15) } as React.CSSProperties}
      />
      <span />
    </div>
  );
}

interface VyshyvankaNotFoundProps {
  className?: string;
  hint?: string;
}

export function VyshyvankaNotFound({
  className,
  hint = "The item does not exist or you do not have access.",
}: VyshyvankaNotFoundProps) {
  const bandRef = useRef<HTMLElement>(null);
  const {
    canvasRef,
    setTopRef,
    setMessageRef,
    setBottomRef,
    playing,
    complete,
  } = useBandEmbroidery(bandRef, data);

  return (
    <article
      ref={bandRef}
      className={clsx(
        "vyshyvanka-band",
        playing && "vyshyvanka-band--playing",
        complete && "vyshyvanka-band--complete",
        className,
      )}
      aria-label="404 Not Found"
    >
      <canvas
        ref={canvasRef}
        className="vyshyvanka-band__canvas"
        aria-hidden="true"
      />

      <div
        ref={setTopRef}
        className="vyshyvanka-band__pattern vyshyvanka-band__pattern--top"
      />

      <section ref={setMessageRef} className="vyshyvanka-band__message">
        <div className="vyshyvanka-band__digits" aria-hidden="true">
          <CrossStitchDigit4 offset={0} />
          <CrossStitchDigit0 offset={15} />
          <CrossStitchDigit4 offset={31} />
        </div>
        <p className="vyshyvanka-band__caption">Not Found</p>
        <p className="vyshyvanka-band__hint">{hint}</p>
      </section>

      <div
        ref={setBottomRef}
        className="vyshyvanka-band__pattern vyshyvanka-band__pattern--bottom"
      />

      <div
        className="vyshyvanka-band__edge-blur vyshyvanka-band__edge-blur--top"
        aria-hidden="true"
      />
      <div
        className="vyshyvanka-band__edge-blur vyshyvanka-band__edge-blur--bottom"
        aria-hidden="true"
      />
    </article>
  );
}
