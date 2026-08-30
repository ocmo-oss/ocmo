import { describe, expect, it } from "vitest";
import { lineKey } from "../yamlCompletion/lineSyntax";
import {
  hasJsonSchemaBaseStructure,
  shouldOfferJsonSchemaRootSnippet,
} from "../yamlCompletion/jsonSchemaCompletion";
import { escapeMonacoSnippetDollars } from "../yamlCompletion/monacoSnippet";
import { JSON_SCHEMA_ROOT_SNIPPET_BODY } from "../yamlCompletion/jsonSchemaCompletion";
import { textModel } from "../yamlCompletion/__tests__/monacoStub";

describe("lineKey", () => {
  it("parses JSON Schema keys that start with $", () => {
    expect(
      lineKey("$schema: https://json-schema.org/draft/2020-12/schema"),
    ).toBe("$schema");
    expect(lineKey('"$schema": https://example.com')).toBe("$schema");
    expect(lineKey("$defs:")).toBe("$defs");
  });
});

describe("escapeMonacoSnippetDollars", () => {
  it("escapes $schema but preserves tab stops", () => {
    expect(escapeMonacoSnippetDollars(JSON_SCHEMA_ROOT_SNIPPET_BODY)).toContain(
      "\\$schema:",
    );
    expect(escapeMonacoSnippetDollars(JSON_SCHEMA_ROOT_SNIPPET_BODY)).toContain(
      "${1:Data title}",
    );
  });
});

describe("shouldOfferJsonSchemaRootSnippet", () => {
  it("returns false when $schema is present", () => {
    const model = textModel(
      "$schema: https://json-schema.org/draft/2020-12/schema\n",
    );
    expect(shouldOfferJsonSchemaRootSnippet(model as never)).toBe(false);
  });

  it("returns false when type and properties are present without $schema", () => {
    const model = textModel("type: object\nproperties: {}\n");
    expect(hasJsonSchemaBaseStructure(model as never)).toBe(true);
    expect(shouldOfferJsonSchemaRootSnippet(model as never)).toBe(false);
  });

  it("returns true for an empty document root", () => {
    const model = textModel("_ocmo:\n  is_json_schema: true\n");
    expect(shouldOfferJsonSchemaRootSnippet(model as never)).toBe(true);
  });
});
