/**
 * Validation schema and propagation targets — config-only URI references.
 */

import { describe, it, expect } from "vitest";

import { buildConfigEditorSchema } from "../../configEditorSchema";
import { __testing } from "../yamlSchemaCompletion";
import {
  resolveUriReferenceScope,
  shouldSuggestUriReferences,
} from "../uriReferenceCompletion";
import { textModel, makePosition, monacoStub } from "./monacoStub";

type JsonSchema = Record<string, unknown>;

const ocmoMetadataSchema: JsonSchema = {
  type: "object",
  properties: {
    validation: { $ref: "#/$defs/ConfigValidationSchema" },
    propagation: { $ref: "#/$defs/ConfigPropagationSchema" },
  },
  $defs: {
    ConfigValidationSchema: {
      type: "object",
      properties: {
        schema: {
          type: "string",
          format: "uri-reference",
          "x-ocmo-uri-reference": "config-only",
        },
      },
    },
    ConfigPropagationSchema: {
      type: "object",
      properties: {
        targets: {
          type: "array",
          items: {
            type: "string",
            format: "uri-reference",
            "x-ocmo-uri-reference": "config-only",
          },
        },
      },
    },
  },
};

function editorSchema(): JsonSchema {
  return buildConfigEditorSchema("_ocmo", ocmoMetadataSchema, null);
}

const uriOptions = {
  namespace: "prod",
  configPath: "app/web",
  metadataKey: "_ocmo",
};

describe("validation and propagation URI completion", () => {
  it("uses config-only scope for validation.schema", () => {
    const schema = editorSchema();
    const validationSchema = (
      schema.$defs?.ConfigValidationSchema?.properties?.schema ?? null
    ) as JsonSchema | null;
    expect(validationSchema?.["x-ocmo-uri-reference"]).toBe("config-only");
    expect(resolveUriReferenceScope(validationSchema, schema)).toBe(
      "config-only",
    );
  });

  it("allows URI browse on empty validation.schema value", () => {
    const yaml = ["_ocmo:", "  validation:", "    schema: "].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(3, 15);
    const ctx = __testing.completionContext(model as never, position as never);
    expect(ctx.kind).toBe("property-value");
    expect(ctx.valuePropertyKey).toBe("schema");
    expect(ctx.objectPath).toEqual(["_ocmo", "validation"]);
    const target = __testing.resolveTargetSchema(
      schema,
      ctx,
      model as never,
      3,
      15,
    );
    expect(
      shouldSuggestUriReferences(target!, schema, ctx, uriOptions, {
        raw: "",
        pathPart: "",
        suffix: "",
        resolvedPrefix: "",
      }),
    ).toBe(true);
  });

  it("allows URI browse on empty propagation.targets array item", () => {
    const yaml = [
      "_ocmo:",
      "  propagation:",
      "    targets:",
      "      - ",
    ].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(4, 9);
    const ctx = __testing.completionContext(model as never, position as never);
    expect(ctx.objectPath).toEqual(["_ocmo", "propagation", "targets"]);
    const target = __testing.resolveTargetSchema(
      schema,
      ctx,
      model as never,
      4,
      9,
    );
    expect(
      shouldSuggestUriReferences(target!, schema, ctx, uriOptions, {
        raw: "",
        pathPart: "",
        suffix: "",
        resolvedPrefix: "",
      }),
    ).toBe(true);
    expect(
      __testing.hasYamlCompletionSuggestions(
        monacoStub as never,
        schema,
        model as never,
        position as never,
        uriOptions,
        { metadataKey: "_ocmo" },
      ),
    ).toBe(true);
  });
});
