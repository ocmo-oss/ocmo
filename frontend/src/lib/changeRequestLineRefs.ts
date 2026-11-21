/** Client-side CR content line references (hash + comment linkify). */

export type CrLineRange = { start: number; end: number };

const FENCED_OR_INLINE_CODE = /(```[\s\S]*?```|`[^`\n]+`)/g;

/** Parse location hash or href fragment: `#10`, `#10-15`, `10-15`. */
export function parseCrLineHash(fragment: string): CrLineRange | null {
  const raw = fragment.replace(/^#/, "").trim();
  const m = /^(\d+)(?:-(\d+))?$/.exec(raw);
  if (!m) return null;
  const start = Number(m[1]);
  const end = Number(m[2] ?? m[1]);
  if (
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    start < 1 ||
    end < 1
  ) {
    return null;
  }
  return { start: Math.min(start, end), end: Math.max(start, end) };
}

export function formatCrLineHash(range: CrLineRange): string {
  return range.start === range.end
    ? String(range.start)
    : `${range.start}-${range.end}`;
}

type LineRefMatch = {
  index: number;
  length: number;
  label: string;
  hash: string;
};

function findLineRefMatches(segment: string): LineRefMatch[] {
  const matches: LineRefMatch[] = [];
  const taken: boolean[] = [];

  const tryAdd = (m: RegExpExecArray, hash: string) => {
    const start = m.index;
    const end = start + m[0].length;
    if (taken.slice(start, end).some(Boolean)) return;
    for (let i = start; i < end; i++) taken[i] = true;
    matches.push({ index: start, length: m[0].length, label: m[0], hash });
  };

  const rangePatterns: RegExp[] = [
    /(?<![\w#])#(\d+)\s*[-:]\s*(\d+)(?!\d)/gi,
    /\blines?\s+(\d+)\s*[-–:]\s*(\d+)\b/gi,
  ];
  for (const re of rangePatterns) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(segment)) !== null) {
      tryAdd(m, `${m[1]}-${m[2]}`);
    }
  }

  const singlePatterns: { re: RegExp; group: number }[] = [
    { re: /(?<![\w#])#(\d+)(?!\d)/gi, group: 1 },
    { re: /\bline\s+(\d+)\b/gi, group: 1 },
  ];
  for (const { re, group } of singlePatterns) {
    re.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(segment)) !== null) {
      tryAdd(m, m[group]);
    }
  }

  return matches.sort((a, b) => a.index - b.index);
}

/** Turn line-reference phrases into markdown links `[text](#10-15)` outside code spans. */
export function linkifyCrLineRefsInMarkdown(markdown: string): string {
  const parts = markdown.split(FENCED_OR_INLINE_CODE);
  return parts
    .map((part, i) => {
      if (i % 2 === 1) return part;
      const matches = findLineRefMatches(part);
      if (matches.length === 0) return part;
      let out = "";
      let cursor = 0;
      for (const match of matches) {
        out += part.slice(cursor, match.index);
        out += `[${match.label}](#${match.hash})`;
        cursor = match.index + match.length;
      }
      out += part.slice(cursor);
      return out;
    })
    .join("");
}

export function isCrLineRefHref(href: string | undefined): boolean {
  if (!href?.startsWith("#")) return false;
  return parseCrLineHash(href) !== null;
}
