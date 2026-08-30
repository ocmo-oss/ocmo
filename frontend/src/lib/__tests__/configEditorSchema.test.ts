import { describe, expect, it } from "vitest";
import {
  buildConfigEditorSchema,
  filterMetadataSchemaForEditor,
} from "../configEditorSchema";

const mockOcmoSchema = {
  type: "object",
  properties: {
    extend: { type: "object", description: "Extend other configs" },
    render: { type: "object", description: "Render templates" },
    is_json_schema: {
      type: "boolean",
      description: "JSON Schema document marker",
    },
  },
};

describe("filterMetadataSchemaForEditor", () => {
  it("keeps is_json_schema in normal config mode", () => {
    const filtered = filterMetadataSchemaForEditor(mockOcmoSchema, false);
    const props = filtered.properties as Record<string, unknown>;
    expect(props.extend).toBeDefined();
    expect(props.render).toBeDefined();
    expect(props.is_json_schema).toBeDefined();
  });

  it("keeps only is_json_schema in json schema config mode", () => {
    const filtered = filterMetadataSchemaForEditor(mockOcmoSchema, true);
    const props = filtered.properties as Record<string, unknown>;
    expect(props.is_json_schema).toBeDefined();
    expect(props.extend).toBeUndefined();
    expect(props.render).toBeUndefined();
  });
});

describe("buildConfigEditorSchema json schema mode", () => {
  it("merges JSON Schema document keywords at the root", () => {
    const composed = buildConfigEditorSchema("_ocmo", mockOcmoSchema, null, {
      isJsonSchemaMode: true,
    });
    const props = composed.properties as Record<string, unknown>;
    expect(props._ocmo).toBeDefined();
    expect(props.type).toBeDefined();
    expect(props.properties).toBeDefined();
    expect(props.$schema).toBeDefined();
  });

  it("marks composed schema as json schema document mode", () => {
    const composed = buildConfigEditorSchema("_ocmo", mockOcmoSchema, null, {
      isJsonSchemaMode: true,
    });
    expect(composed["x-ocmo-json-schema-document"]).toBe(true);
  });

  it("uses consumer data schema in normal mode", () => {
    const dataSchema = {
      type: "object",
      properties: {
        foo: { type: "string" },
      },
    };
    const composed = buildConfigEditorSchema(
      "_ocmo",
      mockOcmoSchema,
      dataSchema,
      {
        isJsonSchemaMode: false,
      },
    );
    const props = composed.properties as Record<string, unknown>;
    expect(props.foo).toBeDefined();
    expect(props.type).toBeUndefined();
  });

  it("uses explicit data schema for builtin policy documents", () => {
    const policySchema = {
      type: "object",
      properties: {
        policies: {
          type: "array",
          items: {
            type: "object",
            properties: {
              actions: {
                type: "array",
                items: {
                  type: "string",
                  enum: ["config:read", "lock:read"],
                },
              },
            },
          },
        },
      },
    };
    const composed = buildConfigEditorSchema(
      "_ocmo",
      mockOcmoSchema,
      policySchema,
      {
        isJsonSchemaMode: true,
        useExplicitDataSchema: true,
      },
    );
    const props = composed.properties as Record<string, unknown>;
    expect(props.policies).toBeDefined();
    expect(props.type).toBeUndefined();
    expect(composed["x-ocmo-json-schema-document"]).toBe(true);
  });
});
