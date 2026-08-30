import { parse, tokenize } from "./jinja2";
import type { editor } from "monaco-editor";
import type * as Monaco from "monaco-editor";

/** Matches API default `OCMO_MAX_TEMPLATE_UPLOAD_BYTES`. */
export const MAX_TEMPLATE_BYTES = 1 * 1024 * 1024;

const JINJA_TOKENIZE_OPTIONS = {
  lstrip_blocks: true,
  trim_blocks: true,
} as const;

const BLOCK_OPEN_TAGS = new Set([
  "for",
  "if",
  "block",
  "macro",
  "filter",
  "call",
  "autoescape",
  "with",
  "raw",
]);

const BLOCK_CLOSE_TO_OPEN: Record<string, string> = {
  endfor: "for",
  endif: "if",
  endblock: "block",
  endmacro: "macro",
  endfilter: "filter",
  endcall: "call",
  endautoescape: "autoescape",
  endwith: "with",
  endraw: "raw",
};

const BLOCK_OPEN_TO_CLOSE: Record<string, string> = Object.fromEntries(
  Object.entries(BLOCK_CLOSE_TO_OPEN).map(([close, open]) => [open, close]),
);

const STATEMENT_TAG_RE = /\{%-?\s*([A-Za-z_]\w*)\b[^%]*?-?%\}/g;

export interface TemplateValidationIssue {
  message: string;
  line: number;
  column: number;
  endLine?: number;
  endColumn?: number;
}

export type TemplateValidationResult =
  { valid: true } | { valid: false; issue: TemplateValidationIssue };

export function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).length;
}

export function validateJinja2Template(
  content: string,
): TemplateValidationResult {
  if (!content.trim()) {
    return {
      valid: false,
      issue: {
        message: "Document content must not be empty",
        line: 1,
        column: 1,
      },
    };
  }

  const byteLength = utf8ByteLength(content);
  if (byteLength > MAX_TEMPLATE_BYTES) {
    return {
      valid: false,
      issue: {
        message: `Template exceeds maximum size of ${MAX_TEMPLATE_BYTES} bytes`,
        line: 1,
        column: 1,
      },
    };
  }

  const blockIssue = findBlockStructureIssue(content);
  if (blockIssue) {
    return {
      valid: false,
      issue: issueAtOffset(content, blockIssue.offset, blockIssue.message),
    };
  }

  try {
    const tokens = tokenize(content, JINJA_TOKENIZE_OPTIONS);
    parse(tokens);
    return { valid: true };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Invalid Jinja2 syntax";
    const issueMessage = message.startsWith("Invalid Jinja2")
      ? message
      : `Invalid Jinja2 syntax: ${message}`;
    return {
      valid: false,
      issue: issueAtOffset(
        content,
        findLikelyErrorOffset(content, message),
        issueMessage,
      ),
    };
  }
}

function issueAtOffset(
  source: string,
  offset: number,
  message: string,
): TemplateValidationIssue {
  const start = offsetToPosition(source, offset);
  const end = tagExtentAt(source, offset);
  return {
    message,
    line: start.line,
    column: start.column,
    endLine: end.line,
    endColumn: end.column,
  };
}

function offsetToPosition(
  source: string,
  offset: number,
): { line: number; column: number } {
  const safeOffset = Math.max(0, Math.min(offset, source.length));
  const before = source.slice(0, safeOffset);
  const lines = before.split("\n");
  return {
    line: lines.length,
    column: (lines[lines.length - 1]?.length ?? 0) + 1,
  };
}

function tagExtentAt(
  source: string,
  offset: number,
): { line: number; column: number } {
  const close = source.indexOf("%}", offset);
  if (close < 0) {
    return offsetToPosition(source, offset);
  }
  const endOffset = source.startsWith("-%}", close) ? close + 3 : close + 2;
  return offsetToPosition(source, endOffset);
}

function findBlockStructureIssue(
  source: string,
): { offset: number; message: string } | null {
  const stack: Array<{ name: string; offset: number }> = [];
  let match: RegExpExecArray | null;

  STATEMENT_TAG_RE.lastIndex = 0;
  while ((match = STATEMENT_TAG_RE.exec(source)) !== null) {
    const tag = match[1];
    const offset = match.index;
    const expectedOpen = BLOCK_CLOSE_TO_OPEN[tag];

    if (expectedOpen) {
      const top = stack[stack.length - 1];
      if (!top || top.name !== expectedOpen) {
        if (top) {
          const expectedClose =
            BLOCK_OPEN_TO_CLOSE[top.name] ?? `end${top.name}`;
          return {
            offset,
            message: `Invalid Jinja2 syntax: expected {% ${expectedClose} %} to close {% ${top.name} %}, found {% ${tag} %}`,
          };
        }
        return {
          offset,
          message: `Invalid Jinja2 syntax: unexpected {% ${tag} %} without matching {% ${expectedOpen} %}`,
        };
      }
      stack.pop();
      continue;
    }

    if (BLOCK_OPEN_TAGS.has(tag)) {
      stack.push({ name: tag, offset });
    }
  }

  const unclosed = stack[stack.length - 1];
  if (unclosed) {
    const expectedClose =
      BLOCK_OPEN_TO_CLOSE[unclosed.name] ?? `end${unclosed.name}`;
    return {
      offset: unclosed.offset,
      message: `Invalid Jinja2 syntax: unclosed {% ${unclosed.name} %} block (expected {% ${expectedClose} %})`,
    };
  }

  return null;
}

function findLikelyErrorOffset(source: string, message: string): number {
  const unclosed = findUnclosedDelimiterOffset(source);
  if (unclosed !== null) {
    return unclosed;
  }

  const unknownStatement = /Unknown statement type: (\w+)/.exec(message);
  if (unknownStatement) {
    const offset = findStatementTagOffset(source, unknownStatement[1]);
    if (offset !== null) return offset;
  }

  if (message.includes("Missing end of comment")) {
    const offset = source.lastIndexOf("{#");
    if (offset >= 0) return offset;
  }

  if (message.includes("Unexpected end of input")) {
    return source.length;
  }

  const charMatch = /Unexpected character: (.)/.exec(message);
  if (charMatch) {
    const inJinja = findCharacterInJinjaRegion(source, charMatch[1]);
    if (inJinja !== null) return inJinja;
  }

  return 0;
}

function findStatementTagOffset(source: string, name: string): number | null {
  const re = new RegExp(`\\{%-?\\s*${name}\\b[^%]*?-?%\\}`, "g");
  let last: number | null = null;
  let match: RegExpExecArray | null;
  while ((match = re.exec(source)) !== null) {
    last = match.index;
  }
  return last;
}

type DelimiterKind = "expr" | "stmt" | "comment";

function findUnclosedDelimiterOffset(source: string): number | null {
  let i = 0;
  const stack: Array<{ kind: DelimiterKind; offset: number }> = [];

  while (i < source.length) {
    if (source.startsWith("{#", i)) {
      stack.push({ kind: "comment", offset: i });
      i += 2;
      continue;
    }
    if (source.startsWith("#}", i) || source.startsWith("-#}", i)) {
      const top = stack[stack.length - 1];
      if (top?.kind === "comment") stack.pop();
      i += source.startsWith("-#}", i) ? 3 : 2;
      continue;
    }
    if (source.startsWith("{{", i)) {
      stack.push({ kind: "expr", offset: i });
      i += 2;
      continue;
    }
    if (source.startsWith("}}", i) || source.startsWith("-}}", i)) {
      const top = stack[stack.length - 1];
      if (top?.kind === "expr") stack.pop();
      i += source.startsWith("-}}", i) ? 3 : 2;
      continue;
    }
    if (source.startsWith("{%", i)) {
      stack.push({ kind: "stmt", offset: i });
      i += 2;
      continue;
    }
    if (source.startsWith("%}", i) || source.startsWith("-%}", i)) {
      const top = stack[stack.length - 1];
      if (top?.kind === "stmt") stack.pop();
      i += source.startsWith("-%}", i) ? 3 : 2;
      continue;
    }
    i += 1;
  }

  const last = stack[stack.length - 1];
  return last?.offset ?? null;
}

function findCharacterInJinjaRegion(
  source: string,
  needle: string,
): number | null {
  const regions: Array<{ start: number; end: number }> = [];
  let i = 0;
  while (i < source.length) {
    if (source.startsWith("{{", i)) {
      const close = source.indexOf("}}", i + 2);
      if (close >= 0) {
        regions.push({ start: i, end: close + 2 });
        i = close + 2;
        continue;
      }
    }
    if (source.startsWith("{%", i)) {
      const close = source.indexOf("%}", i + 2);
      if (close >= 0) {
        regions.push({ start: i, end: close + 2 });
        i = close + 2;
        continue;
      }
    }
    i += 1;
  }

  for (const region of regions) {
    const slice = source.slice(region.start, region.end);
    const local = slice.indexOf(needle);
    if (local >= 0) return region.start + local;
  }
  return null;
}

export function applyTemplateValidationMarkers(
  model: editor.ITextModel,
  monaco: typeof Monaco,
  result: TemplateValidationResult,
): void {
  if (result.valid) {
    monaco.editor.setModelMarkers(model, "jinja2", []);
    return;
  }

  const { line, column, endLine, endColumn, message } = result.issue;
  const lineContent = model.getLineContent(line);
  const startColumn = Math.max(1, Math.min(column, lineContent.length + 1));
  const resolvedEndLine = endLine ?? line;
  const endLineContent = model.getLineContent(resolvedEndLine);
  const resolvedEndColumn =
    endColumn ?? Math.max(startColumn + 1, endLineContent.length + 1);

  monaco.editor.setModelMarkers(model, "jinja2", [
    {
      severity: monaco.MarkerSeverity.Error,
      message,
      startLineNumber: line,
      startColumn,
      endLineNumber: resolvedEndLine,
      endColumn: resolvedEndColumn,
    },
  ]);
}
