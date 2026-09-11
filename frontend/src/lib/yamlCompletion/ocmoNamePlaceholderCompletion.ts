import type * as Monaco from "monaco-editor";
import { stripYamlScalarQuotes } from "./lineSyntax";
import {
  propertyValueCompletionRange,
} from "./ocmoParameterDeclarationCompletion";

const OCMO_METADATA_PREFIX = "._ocmo.";

export const OCMO_NAME_METADATA_SELECTORS = [
  { label: "Name", description: "Name owner leaf segment" },
  { label: "Path", description: "Name owner full path" },
  { label: "Path[-1]", description: "Name owner path segment by index" },
  { label: "Version.tag", description: "Version reference tag used for resolve" },
  { label: "Version.number", description: "Resolved integer version number" },
] as const;

export interface OcmoNamePlaceholderContext {
  partial: string;
  typedSuffix: string;
  replaceRange: Monaco.IRange;
}

function propertyValueBounds(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): { start: number; end: number; fullValue: string; cursorOffset: number } | null {
  const range = propertyValueCompletionRange(model, position);
  if (!range) return null;
  const raw = model.getValueInRange(range);
  const fullValue = stripYamlScalarQuotes(raw);
  const typedRaw = model.getValueInRange({
    startLineNumber: position.lineNumber,
    startColumn: range.startColumn,
    endLineNumber: position.lineNumber,
    endColumn: position.column,
  });
  const typedValue = stripYamlScalarQuotes(typedRaw);
  const quoteLen = raw.startsWith('"') || raw.startsWith("'") ? 1 : 0;
  const cursorOffset = typedValue.length;
  return {
    start: range.startColumn + quoteLen,
    end: range.endColumn,
    fullValue,
    cursorOffset,
  };
}

function placeholderPartialAtCursor(
  fullValue: string,
  cursorOffset: number,
): string | null {
  const beforeCursor = fullValue.slice(0, cursorOffset);
  const openIdx = beforeCursor.lastIndexOf("{");
  if (openIdx < 0) return null;
  if (beforeCursor.indexOf("}", openIdx) >= 0) return null;
  const partial = beforeCursor.slice(openIdx + 1);
  if (!partial.startsWith(".")) return null;
  if (partial === ".") return partial;
  if (partial.startsWith(OCMO_METADATA_PREFIX)) return partial;
  if (partial.startsWith("._ocmo")) return partial;
  return null;
}

export function detectOcmoNamePlaceholderContext(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): OcmoNamePlaceholderContext | null {
  const bounds = propertyValueBounds(model, position);
  if (!bounds) return null;

  const partial = placeholderPartialAtCursor(bounds.fullValue, bounds.cursorOffset);
  if (partial === null) return null;

  const openIdx = bounds.fullValue
    .slice(0, bounds.cursorOffset)
    .lastIndexOf("{");
  const partialStartInValue = openIdx + 1;
  const typedSuffix = partial.slice(1);

  return {
    partial,
    typedSuffix,
    replaceRange: {
      startLineNumber: position.lineNumber,
      startColumn: bounds.start + partialStartInValue,
      endLineNumber: position.lineNumber,
      endColumn: position.column,
    },
  };
}

function metadataInsertText(selectorLabel: string): string {
  return `${OCMO_METADATA_PREFIX}${selectorLabel}`;
}

function selectorMatchesTyped(selectorLabel: string, typedSuffix: string): boolean {
  const full = `_ocmo.${selectorLabel}`;
  if (typedSuffix === "" || typedSuffix === "_ocmo" || typedSuffix === "_ocmo.") {
    return true;
  }
  if (typedSuffix.startsWith("_ocmo.")) {
    const remainder = typedSuffix.slice("_ocmo.".length);
    return selectorLabel.startsWith(remainder);
  }
  return full.startsWith(typedSuffix);
}

function matchingSelectorLabels(typedSuffix: string): string[] {
  return OCMO_NAME_METADATA_SELECTORS.filter((selector) =>
    selectorMatchesTyped(selector.label, typedSuffix),
  ).map((selector) => selector.label);
}

/** Hide widget when typed text already equals the only matching selector. */
export function isUniqueCompleteOcmoNameMetadataMatch(
  partial: string,
  typedSuffix: string,
): boolean {
  const matches = matchingSelectorLabels(typedSuffix);
  if (matches.length !== 1) return false;
  return partial === `${OCMO_METADATA_PREFIX}${matches[0]}`;
}

export function shouldSuggestOcmoNameMetadata(
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): boolean {
  const ctx = detectOcmoNamePlaceholderContext(model, position);
  if (!ctx) return false;
  if (isUniqueCompleteOcmoNameMetadataMatch(ctx.partial, ctx.typedSuffix)) {
    return false;
  }
  return matchingSelectorLabels(ctx.typedSuffix).length > 0;
}

export function buildOcmoNameMetadataCompletions(
  monaco: typeof Monaco,
  model: Monaco.editor.ITextModel,
  position: Monaco.Position,
): Monaco.languages.CompletionItem[] {
  const ctx = detectOcmoNamePlaceholderContext(model, position);
  if (!ctx) return [];
  if (isUniqueCompleteOcmoNameMetadataMatch(ctx.partial, ctx.typedSuffix)) {
    return [];
  }

  return OCMO_NAME_METADATA_SELECTORS.filter((selector) =>
    selectorMatchesTyped(selector.label, ctx.typedSuffix),
  ).map((selector, index) => {
    const insertText = metadataInsertText(selector.label);
    return {
      label: {
        label: `${OCMO_METADATA_PREFIX}${selector.label}`,
        description: "name metadata",
      },
      kind: monaco.languages.CompletionItemKind.Value,
      insertText,
      range: ctx.replaceRange,
      filterText: `${OCMO_METADATA_PREFIX}${selector.label}`,
      sortText: `!${index.toString().padStart(3, "0")}:${selector.label}`,
      detail: "output name metadata",
      documentation: {
        value: selector.description,
        isTrusted: true,
      },
    };
  });
}

export const __testingOcmoNamePlaceholderCompletion = {
  placeholderPartialAtCursor,
  propertyValueBounds,
};
