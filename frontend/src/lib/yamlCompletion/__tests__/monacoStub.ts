/**
 * Minimal Monaco stub for unit-testing the YAML completion logic in Node.
 * Only the model methods and enums actually called by the completion code are implemented.
 */

export interface IRange {
  startLineNumber: number;
  startColumn: number;
  endLineNumber: number;
  endColumn: number;
}

export interface IPosition {
  lineNumber: number;
  column: number;
}

export interface IWordAtPosition {
  word: string;
  startColumn: number;
  endColumn: number;
}

/** Create a stub ITextModel from a YAML string. */
export function textModel(yaml: string) {
  const lines = yaml.split("\n");

  function getLineContent(lineNumber: number): string {
    return lines[lineNumber - 1] ?? "";
  }

  function getLineCount(): number {
    return lines.length;
  }

  function getValueInRange(range: IRange): string {
    const { startLineNumber, startColumn, endLineNumber, endColumn } = range;
    if (startLineNumber === endLineNumber) {
      return getLineContent(startLineNumber).slice(
        startColumn - 1,
        endColumn - 1,
      );
    }
    const parts: string[] = [];
    for (let ln = startLineNumber; ln <= endLineNumber; ln++) {
      const line = getLineContent(ln);
      if (ln === startLineNumber) {
        parts.push(line.slice(startColumn - 1));
      } else if (ln === endLineNumber) {
        parts.push(line.slice(0, endColumn - 1));
      } else {
        parts.push(line);
      }
    }
    return parts.join("\n");
  }

  function getWordUntilPosition(pos: IPosition): IWordAtPosition {
    const line = getLineContent(pos.lineNumber);
    const before = line.slice(0, pos.column - 1);
    const match = before.match(/(\w+)$/);
    if (!match) {
      return { word: "", startColumn: pos.column, endColumn: pos.column };
    }
    const word = match[1];
    return {
      word,
      startColumn: pos.column - word.length,
      endColumn: pos.column,
    };
  }

  function getValue(): string {
    return yaml;
  }

  function getVersionId(): number {
    return 1;
  }

  function getLanguageId(): string {
    return "yaml";
  }

  return {
    getLineContent,
    getLineCount,
    getValueInRange,
    getWordUntilPosition,
    getValue,
    getVersionId,
    getLanguageId,
  };
}

export function makePosition(lineNumber: number, column: number): IPosition {
  return { lineNumber, column };
}

/** Monaco enum stubs matching the numeric values in monaco.d.ts. */
export const monacoStub = {
  languages: {
    CompletionItemKind: {
      Text: 0,
      Method: 1,
      Function: 2,
      Constructor: 3,
      Field: 4,
      Variable: 5,
      Class: 6,
      Interface: 7,
      Module: 8,
      Property: 9,
      Unit: 10,
      Value: 11,
      Enum: 12,
      Keyword: 13,
      Snippet: 14,
      Color: 15,
      File: 16,
      Reference: 17,
      Folder: 18,
      EnumMember: 19,
      Constant: 20,
      Struct: 21,
      Event: 22,
      Operator: 23,
      TypeParameter: 24,
    },
    CompletionItemInsertTextRule: {
      None: 0,
      KeepWhitespace: 1,
      InsertAsSnippet: 4,
    },
  },
} as const;
