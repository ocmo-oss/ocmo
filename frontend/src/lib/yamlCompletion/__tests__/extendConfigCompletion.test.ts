/**
 * Extend configs array completion — string path refs and object-form refs.
 */

import { describe, it, expect } from "vitest";

import { buildConfigEditorSchema } from "../../configEditorSchema";
import { __testing } from "../yamlSchemaCompletion";
import {
  extractTypedUriReference,
  hasUriReferenceFormat,
  resolveUriReferenceScope,
  shouldSuggestUriReferences,
} from "../uriReferenceCompletion";
import { textModel, makePosition, monacoStub } from "./monacoStub";

type JsonSchema = Record<string, unknown>;

const extendRefObjectSchema = {
  type: "object",
  additionalProperties: false,
  required: ["path"],
  properties: {
    path: {
      type: "string",
      format: "uri-reference",
      "x-ocmo-uri-reference": "config-only",
      description: "Config path to merge",
    },
    key: {
      type: "string",
      description: "Optional selector into the source document",
    },
    as: {
      type: "string",
      description: "Optional destination selector in the merge target",
    },
    skip_missing: {
      type: "boolean",
      default: false,
      description: "Skip when path or version/tag is absent",
    },
  },
};

const ocmoMetadataSchema: JsonSchema = {
  type: "object",
  properties: {
    extend: {
      $ref: "#/$defs/ConfigExtendSchema",
    },
  },
  $defs: {
    ConfigExtendRefSchema: extendRefObjectSchema,
    ConfigExtendSchema: {
      type: "object",
      properties: {
        configs: {
          type: "array",
          items: {
            anyOf: [
              {
                type: "string",
                format: "uri-reference",
                "x-ocmo-uri-reference": "config-only",
              },
              { $ref: "#/$defs/ConfigExtendRefSchema" },
            ],
          },
        },
        mode: {
          type: "string",
          enum: ["stack", "broadcast", "zip", "replicate"],
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

async function getSuggestionItems(
  yaml: string,
  lineNumber: number,
  column: number,
  uriOpts: typeof uriOptions | null = uriOptions,
) {
  const schema = editorSchema();
  const model = textModel(yaml);
  const position = makePosition(lineNumber, column);
  const result = __testing.buildYamlCompletionSuggestions(
    monacoStub as never,
    schema,
    model as never,
    position as never,
    uriOpts,
    { metadataKey: "_ocmo" },
  );
  return result instanceof Promise ? await result : result;
}

const uriOptions = {
  namespace: "prod",
  configPath: "app/web",
  metadataKey: "_ocmo",
};

describe("extend configs array completion", () => {
  it("uses config-only URI scope for extend refs", () => {
    const schema = editorSchema();
    const extendRefProperties = schemaDefs(schema).ConfigExtendRefSchema
      ?.properties as Record<string, JsonSchema> | undefined;
    const extendRefPath = extendRefProperties?.path ?? {};
    expect(extendRefPath["x-ocmo-uri-reference"]).toBe("config-only");
    const extendProperties = schemaDefs(schema).ConfigExtendSchema
      ?.properties as Record<string, JsonSchema> | undefined;
    const configsItems = (
      extendProperties?.configs as { items?: { anyOf?: JsonSchema[] } }
    )?.items;
    const stringBranch = configsItems?.anyOf?.find(
      (branch) => branch.format === "uri-reference",
    );
    expect(stringBranch?.["x-ocmo-uri-reference"]).toBe("config-only");
    expect(resolveUriReferenceScope(stringBranch ?? null, schema)).toBe(
      "config-only",
    );
  });

  it("allows URI browse on empty array-item dash in metadata", () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      - "].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(4, 9);
    const ctx = __testing.completionContext(model as never, position as never);
    const target = __testing.resolveTargetSchema(
      schema,
      ctx,
      model as never,
      4,
      9,
    );
    expect(
      extractTypedUriReference(model as never, position as never, ctx),
    ).toEqual({
      raw: "",
      pathPart: "",
      suffix: "",
      resolvedPrefix: "",
    });
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

  it("resolves extend $ref when locating configs array schema", () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      - "].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(4, 9);
    const ctx = __testing.completionContext(model as never, position as never);
    const arraySchema = __testing.schemaAtPath(schema, ctx.objectPath, {
      enterArrayItemBefore: ctx.arrayItemEnterBefore,
    });
    expect(arraySchema).toBeTruthy();
    expect(JSON.stringify(arraySchema?.items)).toContain("anyOf");
  });

  it("resolves path property schema inside object-form extend refs", () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      - path: "].join(
      "\n",
    );
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(4, 16);
    const ctx = __testing.completionContext(model as never, position as never);
    expect(ctx.kind).toBe("property-value");
    expect(ctx.valuePropertyKey).toBe("path");
    expect(ctx.insideArrayItem).toBe(true);
    const target = __testing.resolveTargetSchema(
      schema,
      ctx,
      model as never,
      4,
      16,
    );
    expect(target?.format).toBe("uri-reference");
    expect(
      shouldSuggestUriReferences(target!, schema, ctx, uriOptions, {
        raw: "",
        pathPart: "",
        suffix: "",
        resolvedPrefix: "",
      }),
    ).toBe(true);
  });

  it("resolves nested path property schema in multiline object-form extend refs", () => {
    const yaml = [
      "_ocmo:",
      "  extend:",
      "    configs:",
      "      -",
      "        path: ",
    ].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(5, 14);
    const ctx = __testing.completionContext(model as never, position as never);
    expect(ctx.kind).toBe("property-value");
    expect(ctx.valuePropertyKey).toBe("path");
    expect(ctx.insideArrayItem).toBe(true);
    const target = __testing.resolveTargetSchema(
      schema,
      ctx,
      model as never,
      5,
      14,
    );
    expect(target?.format).toBe("uri-reference");
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

  it("offers URI suggestions on scalar extend ref after a prior object-form item", () => {
    const yaml = [
      "_ocmo:",
      "  extend:",
      "    mode: replicate",
      "    by: .data",
      "    configs:",
      "      - ../bases/base",
      "      - path: ../bases/business",
      "        skip_missing: false",
      "      - ../",
    ].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(9, 11);
    const ctx = __testing.completionContext(model as never, position as never);
    expect(ctx.kind).toBe("array-item");
    expect(ctx.objectPath).toEqual(["_ocmo", "extend", "configs"]);
    const target = __testing.resolveTargetSchema(
      schema,
      ctx,
      model as never,
      9,
      11,
    );
    expect(target).toBeTruthy();
    expect(hasUriReferenceFormat(target!, schema)).toBe(true);
    const typed = extractTypedUriReference(
      model as never,
      position as never,
      ctx,
    );
    expect(typed?.pathPart).toBe("..");
    expect(
      shouldSuggestUriReferences(target!, schema, ctx, uriOptions, typed),
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

  it("does not suggest array items on a blank row before '-'", async () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      "].join("\n");
    const schema = editorSchema();
    const model = textModel(yaml);
    const position = makePosition(4, 7);
    expect(
      __testing.hasYamlCompletionSuggestions(
        monacoStub as never,
        schema,
        model as never,
        position as never,
        uriOptions,
        { metadataKey: "_ocmo" },
      ),
    ).toBe(false);
    const items = await getSuggestionItems(yaml, 4, 7);
    expect(
      items.filter((item) => String(item.label).includes("Extend source")),
    ).toHaveLength(0);
  });

  it("offers object-form snippets alongside string refs on a new array item", async () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      - "].join("\n");
    const items = await getSuggestionItems(yaml, 4, 9);
    const objectSnippet = items.find((item) =>
      String(item.insertText).includes("path:"),
    );
    expect(objectSnippet).toBeDefined();
    expect(String(objectSnippet?.insertText)).toMatch(/path:\s/);
  });

  it("includes skip_missing in object-form all-fields snippet", async () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      - "].join("\n");
    const items = await getSuggestionItems(yaml, 4, 9);
    const objectSnippet = items.find((item) =>
      String(item.insertText).includes("skip_missing"),
    );
    expect(objectSnippet).toBeDefined();
    expect(String(objectSnippet?.insertText)).toContain("path:");
  });

  it("labels extend object snippets for discoverability", async () => {
    const yaml = ["_ocmo:", "  extend:", "    configs:", "      - "].join("\n");
    const items = await getSuggestionItems(yaml, 4, 9);
    const extendItems = items.filter((item) =>
      String(item.label).includes("Extend source"),
    );
    expect(extendItems.length).toBeGreaterThanOrEqual(2);
    expect(extendItems[0]?.sortText?.startsWith("!!")).toBe(true);
    expect(extendItems[0]?.filterText).toContain("object");
    expect(
      extendItems.some((item) =>
        String(item.insertText).includes("skip_missing"),
      ),
    ).toBe(true);
  });
});
