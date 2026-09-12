/**
 * Render templates array completion — template-only URI references.
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
    render: {
      $ref: "#/$defs/ConfigRenderSchema",
    },
  },
  $defs: {
    ConfigRenderSchema: {
      type: "object",
      properties: {
        templates: {
          type: "array",
          items: {
            type: "string",
            format: "uri-reference",
            "x-ocmo-uri-reference": "template-only",
          },
        },
        mode: {
          type: "string",
          enum: ["broadcast", "zip", "replicate"],
        },
      },
    },
  },
};

function editorSchema(): JsonSchema {
  return buildConfigEditorSchema("_ocmo", ocmoMetadataSchema, null);
}

function schemaDefs(schema: JsonSchema): Record<string, JsonSchema> {
  return (schema.$defs ?? {}) as Record<string, JsonSchema>;
}

const uriOptions = {
  namespace: "prod",
  configPath: "app/web",
  metadataKey: "_ocmo",
};

describe("render templates array completion", () => {
  it("uses template-only URI scope for render template refs", () => {
    const schema = editorSchema();
    const renderProperties = schemaDefs(schema).ConfigRenderSchema
      ?.properties as Record<string, JsonSchema> | undefined;
    const templatesItems = (
      renderProperties?.templates as { items?: JsonSchema }
    )?.items;
    expect(templatesItems?.["x-ocmo-uri-reference"]).toBe("template-only");
    expect(resolveUriReferenceScope(templatesItems ?? null, schema)).toBe(
      "template-only",
    );
  });

  it("allows URI browse on empty render template array item", () => {
    const yaml = ["_ocmo:", "  render:", "    templates:", "      - "].join(
      "\n",
    );
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(4, 9);
    const ctx = __testing.completionContext(model as never, position as never);
    expect(ctx.objectPath).toEqual(["_ocmo", "render", "templates"]);
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
