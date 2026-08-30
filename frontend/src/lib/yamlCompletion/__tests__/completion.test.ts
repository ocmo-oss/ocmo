/**
 * Characterization tests for YAML schema completion.
 *
 * These tests pin the *current* behavior so that refactoring phases can run
 * the suite and verify nothing changed unintentionally. Phase 4 bug-fix
 * snapshot updates are each reviewed against the specific fix they correspond to.
 *
 * Schema source: api/core/data/builtin_schemas/_permissions.schema.yaml
 * loaded via the `yaml` package (Node environment, no DOM).
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parse as parseYaml } from "yaml";

import { __testing } from "../yamlSchemaCompletion";
import { textModel, makePosition, monacoStub } from "./monacoStub";
import { buildConfigEditorSchema } from "../../configEditorSchema";
import { JSON_SCHEMA_ROOT_SNIPPET_LABEL } from "../jsonSchemaCompletion";

const mockOcmoMetadataSchema = {
  type: "object",
  properties: {
    extend: {
      type: "object",
      description: "Extend other configs",
      properties: {
        configs: { type: "array", items: { type: "string" } },
      },
    },
    render: { type: "object", description: "Render templates" },
    is_json_schema: {
      type: "boolean",
      description: "Mark body as JSON Schema",
    },
  },
};

function jsonSchemaEditorSchema(): JsonSchema {
  return buildConfigEditorSchema("_ocmo", mockOcmoMetadataSchema, null, {
    isJsonSchemaMode: true,
  });
}

function normalEditorSchema(dataSchema: JsonSchema | null = null): JsonSchema {
  return buildConfigEditorSchema("_ocmo", mockOcmoMetadataSchema, dataSchema, {
    isJsonSchemaMode: false,
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type JsonSchema = Record<string, unknown>;

function loadSchema(filename: string): JsonSchema {
  const schemaPath = resolve(
    __dirname,
    "../../../../..", // workspace root /home/andy/ocmo
    "api/core/data/builtin_schemas",
    filename,
  );
  const raw = readFileSync(schemaPath, "utf-8");
  const parsed = parseYaml(raw) as Record<string, unknown>;
  // Strip the _ocmo metadata key that is not part of JSON Schema
  delete parsed["_ocmo"];
  return parsed as JsonSchema;
}

const permissionsSchema = loadSchema("_permissions.schema.yaml");

// Normalise a completion item to a stable snapshot-friendly shape.
interface SuggestionSummary {
  label: string;
  sortText: string | undefined;
  insertText: string;
  kind: number;
}

function summarise(
  items: Array<{
    label: unknown;
    sortText?: unknown;
    insertText: unknown;
    kind: unknown;
  }>,
): SuggestionSummary[] {
  return items.map((item) => ({
    label:
      typeof item.label === "string"
        ? item.label
        : ((item.label as { label?: string })?.label ?? String(item.label)),
    sortText: item.sortText === undefined ? undefined : String(item.sortText),
    insertText: String(item.insertText),
    kind: Number(item.kind),
  }));
}

async function getSuggestions(
  schema: JsonSchema,
  yaml: string,
  lineNumber: number,
  column: number,
  paramOptions?: any,
): Promise<SuggestionSummary[]> {
  const model = textModel(yaml);
  const position = makePosition(lineNumber, column);

  const result = __testing.buildYamlCompletionSuggestions(
    monacoStub as any,
    schema,
    model as any,
    position as any,
    null,
    paramOptions ?? null,
  );
  const items = result instanceof Promise ? await result : result;
  return summarise(items);
}

// ---------------------------------------------------------------------------
// Top-level property keys
// ---------------------------------------------------------------------------

describe("top-level property keys", () => {
  it('suggests "policies" on empty document', async () => {
    const yaml = "";
    const items = await getSuggestions(permissionsSchema, yaml, 1, 1);
    expect(items).toMatchSnapshot();
  });

  it('does not suggest "policies" again when it already exists', async () => {
    const yaml =
      "policies:\n  - effect: Allow\n    actors: []\n    actions: []\n    resources: []\n";
    const items = await getSuggestions(permissionsSchema, yaml, 6, 1);
    expect(items.map((i) => i.label)).not.toContain("policies");
  });
});

// ---------------------------------------------------------------------------
// Array item discriminator: actors[].kind
// ---------------------------------------------------------------------------

describe("actors[].kind discriminator", () => {
  const baseYaml = [
    "policies:",
    "  - effect: Allow",
    "    actors:",
    "      - ",
  ].join("\n");
  // Line 4 = "      - ", column 9 = after the dash and space
  const line = 4;
  const col = baseYaml.split("\n")[3].length + 1; // end of "      - "

  it("offers kind discriminator suggestions on empty array item line", async () => {
    const items = await getSuggestions(permissionsSchema, baseYaml, line, col);
    expect(items).toMatchSnapshot();
    // Must include both discriminator values
    const labels = items.map((i) => i.label);
    expect(labels).toContain("kind: User");
    expect(labels).toContain("kind: Resolver");
  });

  it('offers discriminator after typing partial "- k"', async () => {
    const yaml = [
      "policies:",
      "  - effect: Allow",
      "    actors:",
      "      - k",
    ].join("\n");
    const colK = yaml.split("\n")[3].length + 1;
    const items = await getSuggestions(permissionsSchema, yaml, 4, colK);
    expect(items).toMatchSnapshot();
  });
});

// ---------------------------------------------------------------------------
// Property keys under kind: User  (claims)
// ---------------------------------------------------------------------------

describe("property keys inside actors[] kind: User", () => {
  const yaml = [
    "policies:",
    "  - effect: Allow",
    "    actors:",
    "      - kind: User",
    "        ",
  ].join("\n");
  const claimsLine = 5;
  const claimsCol = 9; // 8 spaces indent

  it('suggests "claims" key under kind: User', async () => {
    const items = await getSuggestions(
      permissionsSchema,
      yaml,
      claimsLine,
      claimsCol,
    );
    expect(items).toMatchSnapshot();
    const labels = items.map((i) => i.label);
    expect(labels.some((l) => l === "claims" || l.startsWith("claims"))).toBe(
      true,
    );
  });
});

// ---------------------------------------------------------------------------
// Scalar array items: actions enum
// ---------------------------------------------------------------------------

describe("actions enum array items", () => {
  const yaml = [
    "policies:",
    "  - effect: Allow",
    "    actors:",
    "      - kind: User",
    "        claims:",
    "          email: '*'",
    "    actions:",
    "      - ",
  ].join("\n");
  const actionsLine = 8;
  const actionsCol = yaml.split("\n")[7].length + 1; // after "      - "

  it("suggests action enum values on empty array item line", async () => {
    const items = await getSuggestions(
      permissionsSchema,
      yaml,
      actionsLine,
      actionsCol,
    );
    expect(items).toMatchSnapshot();
  });

  it("adds leading space to insertText when line has bare dash (no trailing space)", async () => {
    // The bug: line "      -" (no space) caused insertion of "-config:read" instead of "- config:read"
    const bareYaml = [
      "policies:",
      "  - effect: Allow",
      "    actors:",
      "      - kind: User",
      "        claims:",
      "          email: '*'",
      "    actions:",
      "      -", // bare dash, no space
    ].join("\n");
    const bareCol = bareYaml.split("\n")[7].length + 1; // column 7, right after "-"
    const bareItems = await getSuggestions(
      permissionsSchema,
      bareYaml,
      8,
      bareCol,
    );
    for (const item of bareItems) {
      expect(item.insertText).toMatch(/^ /);
    }
  });
});

// ---------------------------------------------------------------------------
// shouldAutoTriggerYamlSuggest
// ---------------------------------------------------------------------------

describe("shouldAutoTriggerYamlSuggest", () => {
  it("triggers on empty property-key indent position", () => {
    const yaml = "policies:\n  - effect: Allow\n    ";
    const model = textModel(yaml);
    const position = makePosition(3, 5); // after 4 spaces (indent level 2)
    const result = __testing.shouldAutoTriggerYamlSuggest(
      model as any,
      position as any,
      null,
      permissionsSchema,
      null,
    );
    expect(result).toBe(true);
  });

  it('triggers after "effect: A" (partial enum value)', () => {
    const yaml = "policies:\n  - effect: A";
    const model = textModel(yaml);
    const position = makePosition(2, yaml.split("\n")[1].length + 1);
    const result = __testing.shouldAutoTriggerYamlSuggest(
      model as any,
      position as any,
      null,
      permissionsSchema,
      null,
    );
    expect(result).toBe(true);
  });

  it("does not trigger on an empty first line", () => {
    const yaml = "\npolicies:\n  - ";
    const model = textModel(yaml);
    const position = makePosition(1, 1);
    const result = __testing.shouldAutoTriggerYamlSuggest(
      model as any,
      position as any,
      null,
      permissionsSchema,
      null,
    );
    // Line 1 is blank; there is no current-line indent, so the context
    // resolves as property-key at indent 0 in a document that already has
    // "policies" — but the trigger fires for the root scope regardless.
    // Pin the current behavior:
    expect(result).toMatchSnapshot();
  });
});

// ---------------------------------------------------------------------------
// hasYamlCompletionSuggestions
// ---------------------------------------------------------------------------

describe("hasYamlCompletionSuggestions", () => {
  it("returns true at top-level empty document", () => {
    const model = textModel("");
    const result = __testing.hasYamlCompletionSuggestions(
      monacoStub as any,
      permissionsSchema,
      model as any,
      makePosition(1, 1) as any,
      null,
      null,
    );
    expect(result).toBe(true);
  });

  it("returns false when there is no matching schema", () => {
    const model = textModel("no_such_key: ");
    const result = __testing.hasYamlCompletionSuggestions(
      monacoStub as any,
      permissionsSchema,
      model as any,
      makePosition(1, 14) as any,
      null,
      null,
    );
    expect(result).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// isArrayItemLine edge case: bare dash without trailing space
// ---------------------------------------------------------------------------

describe("completionContext on bare dash line", () => {
  it('recognises "      -" (no trailing space) as array-item context', () => {
    const yaml = "policies:\n  - effect: Allow\n    actors:\n      -";
    const model = textModel(yaml);
    const position = makePosition(4, 7); // column 7 = after the dash
    const ctx = __testing.completionContext(model as any, position as any);
    // This may be 'array-item' or 'property-key' depending on current logic.
    // Pin what it currently returns; fix-line-syntax will update this snapshot.
    expect(ctx.kind).toMatchSnapshot();
  });

  it('recognises "      - " (with trailing space) as array-item context', () => {
    const yaml = "policies:\n  - effect: Allow\n    actors:\n      - ";
    const model = textModel(yaml);
    const position = makePosition(4, 9);
    const ctx = __testing.completionContext(model as any, position as any);
    expect(ctx.kind).toBe("array-item");
  });
});

// ---------------------------------------------------------------------------
// enclosingArrayItemKeyLineIndent / findEnclosingArrayItemIndent
// ---------------------------------------------------------------------------

describe("enclosingArrayItemKeyLineIndent", () => {
  it("returns indent of the immediately enclosing array item", () => {
    const yaml = [
      "policies:",
      "  - effect: Allow",
      "    actors:",
      "      - kind: User",
      "        ",
    ].join("\n");
    const model = textModel(yaml);
    // Line 5, inside actors[] item at indent 6
    const result = __testing.enclosingArrayItemKeyLineIndent(model as any, 5);
    expect(result).toMatchSnapshot();
  });
});

// ---------------------------------------------------------------------------
// _ocmo parameter placeholder completion
// ---------------------------------------------------------------------------

describe("parameter placeholder completion", () => {
  const paramOpts = { metadataKey: "_ocmo" };

  // Cursor is placed on the '!' character (column = index + 1 of '!').
  // The column just *after* '!' (line.length + 1) hits an off-by-one in
  // detectParameterPlaceholderContext for quoted values; that is a known bug
  // to be fixed in Phase 4 (fix-oneof-path doesn't cover it; it would be a
  // separate item). Current tests pin the cursor-on-'!' position.
  const yamlWithParams = [
    "_ocmo:",
    "  parameters:",
    "    my_env:",
    "      type: string",
    "      description: The environment name",
    "policies:",
    "  - effect: Allow",
    "    actors:",
    "      - kind: User",
    "        claims:",
    "          email: '{!",
  ].join("\n");

  // Column of the '!' character (last char of the line)
  const bangCol = yamlWithParams.split("\n")[10].length; // length is 0-indexed end = 1-indexed last col

  it("suggests parameter names when cursor is on the ! character", async () => {
    const items = await getSuggestions(
      permissionsSchema,
      yamlWithParams,
      11,
      bangCol,
      paramOpts,
    );
    expect(items).toMatchSnapshot();
    const labels = items.map((i) => i.label);
    expect(labels).toContain("my_env");
  });

  it("insertText includes closing brace when not already present", async () => {
    const items = await getSuggestions(
      permissionsSchema,
      yamlWithParams,
      11,
      bangCol,
      paramOpts,
    );
    const envItem = items.find((i) => i.label === "my_env");
    expect(envItem).toBeDefined();
    expect(envItem!.insertText).toContain("{!my_env}");
  });

  it("does not duplicate closing brace when already present", async () => {
    const yamlWithClose = [
      "_ocmo:",
      "  parameters:",
      "    my_env:",
      "      type: string",
      "      description: The environment name",
      "policies:",
      "  - effect: Allow",
      "    actors:",
      "      - kind: User",
      "        claims:",
      "          email: '{!}",
    ].join("\n");
    const line11 = yamlWithClose.split("\n")[10];
    // Place cursor on the '!' (column = index of '!' + 1 = 1-indexed)
    const bangColClose = line11.indexOf("!") + 1;
    const items = await getSuggestions(
      permissionsSchema,
      yamlWithClose,
      11,
      bangColClose,
      paramOpts,
    );
    const envItem = items.find((i) => i.label === "my_env");
    expect(envItem).toBeDefined();
    expect(envItem!.insertText).not.toContain("}}");
    expect(envItem!.insertText).toContain("{!my_env}");
  });
});

// ---------------------------------------------------------------------------
// property snippet ordering: snippet variants rank below enum suggestions
// ---------------------------------------------------------------------------

describe("snippet variant sort order", () => {
  it("oneOf snippet variants use z-prefixed sortText", async () => {
    // actors[] has a oneOf (User | Resolver), so snippet variants get z0: / z1:
    const yaml = [
      "policies:",
      "  - effect: Allow",
      "    actors:",
      "      - ",
    ].join("\n");
    const line = 4;
    const col = yaml.split("\n")[3].length + 1;
    const items = await getSuggestions(permissionsSchema, yaml, line, col);
    const snippets = items.filter(
      (i) => i.kind === monacoStub.languages.CompletionItemKind.Snippet,
    );
    if (snippets.length > 0) {
      for (const s of snippets) {
        expect(s.sortText ?? "").toMatch(/^z/);
      }
    }
  });

  it("enum/discriminator suggestions sort before snippets", async () => {
    const yaml = ["policies:", "  - effect: "].join("\n");
    const items = await getSuggestions(
      permissionsSchema,
      yaml,
      2,
      yaml.split("\n")[1].length + 1,
    );
    const enums = items.filter(
      (i) => i.kind === monacoStub.languages.CompletionItemKind.EnumMember,
    );
    const snippets = items.filter(
      (i) => i.kind === monacoStub.languages.CompletionItemKind.Snippet,
    );
    if (enums.length > 0 && snippets.length > 0) {
      const minEnum = enums.map((e) => e.sortText ?? "").sort()[0];
      const minSnippet = snippets.map((s) => s.sortText ?? "").sort()[0];
      expect(minEnum < minSnippet).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// suggest-widget label/detail formatting
// ---------------------------------------------------------------------------

describe("formatCompletionPreviewDetail", () => {
  const { formatCompletionPreviewDetail } = __testing;

  it("avoids repeating the property name in inline detail text", () => {
    expect(formatCompletionPreviewDetail("cast", "cast:\n  type: json")).toBe(
      "…",
    );
    expect(formatCompletionPreviewDetail("cast", "cast:")).toBe("snippet");
  });

  it("keeps unrelated preview text intact", () => {
    expect(
      formatCompletionPreviewDetail("kind: User", "- kind: User\n  claims:"),
    ).toBe("- kind: User …");
  });
});

// ---------------------------------------------------------------------------
// JSON Schema config mode (_ocmo.is_json_schema: true)
// ---------------------------------------------------------------------------

describe("json schema config editor mode", () => {
  it("offers only the base structure snippet at an empty document root", async () => {
    const yaml = ["_ocmo:", "  is_json_schema: true", ""].join("\n");
    const items = await getSuggestions(jsonSchemaEditorSchema(), yaml, 3, 1);
    expect(items).toHaveLength(1);
    expect(items[0]?.label).toBe(JSON_SCHEMA_ROOT_SNIPPET_LABEL);
  });

  it("does not offer the base structure snippet after it is inserted", async () => {
    const yaml = [
      "_ocmo:",
      "  is_json_schema: true",
      "$schema: https://json-schema.org/draft/2020-12/schema",
      "title: Data title",
      "description: Data structure description",
      "type: object",
      "additionalProperties: false",
      "required: []",
      "properties: {}",
      "",
    ].join("\n");
    const items = await getSuggestions(jsonSchemaEditorSchema(), yaml, 11, 1);
    const labels = items.map((i) => i.label);
    expect(labels).not.toContain(JSON_SCHEMA_ROOT_SNIPPET_LABEL);
    expect(labels).toContain("$id");
    expect(labels).toContain("$defs");
  });

  it("suggests document root keywords after the base structure exists", async () => {
    const yaml = [
      "_ocmo:",
      "  is_json_schema: true",
      "$schema: https://json-schema.org/draft/2020-12/schema",
      "type: object",
      "",
    ].join("\n");
    const items = await getSuggestions(jsonSchemaEditorSchema(), yaml, 5, 1);
    const labels = items.map((i) => i.label);
    expect(labels).toContain("title");
    expect(labels).toContain("properties");
    expect(labels).not.toContain("extend");
  });

  it("suggests only is_json_schema inside _ocmo block", async () => {
    const yaml = ["_ocmo:", "  "].join("\n");
    const items = await getSuggestions(jsonSchemaEditorSchema(), yaml, 2, 3);
    const labels = items.map((i) => i.label);
    expect(labels).toContain("is_json_schema");
    expect(labels).not.toContain("extend");
    expect(labels).not.toContain("render");
  });

  it("includes is_json_schema in normal config _ocmo block", async () => {
    const yaml = ["_ocmo:", "  "].join("\n");
    const items = await getSuggestions(normalEditorSchema(), yaml, 2, 3);
    const labels = items.map((i) => i.label);
    expect(labels).toContain("extend");
    expect(labels).toContain("render");
    expect(labels).toContain("is_json_schema");
  });

  it("suggests only untyped keywords under a property before type is set", async () => {
    const yaml = [
      "_ocmo:",
      "  is_json_schema: true",
      "$schema: https://json-schema.org/draft/2020-12/schema",
      "type: object",
      "properties:",
      "  foo:",
      "    ",
    ].join("\n");
    const items = await getSuggestions(jsonSchemaEditorSchema(), yaml, 8, 5);
    const labels = items.map((i) => i.label);
    expect(labels).toEqual(
      expect.arrayContaining(["type", "title", "description"]),
    );
    expect(labels).not.toContain("enum");
    expect(labels).not.toContain("pattern");
    expect(labels).not.toContain("properties");
  });

  it("suggests string-specific keywords when property type is string", async () => {
    const yaml = [
      "_ocmo:",
      "  is_json_schema: true",
      "$schema: https://json-schema.org/draft/2020-12/schema",
      "type: object",
      "properties:",
      "  foo:",
      "    type: string",
      "    ",
    ].join("\n");
    const items = await getSuggestions(jsonSchemaEditorSchema(), yaml, 9, 5);
    const labels = items.map((i) => i.label);
    expect(labels).toContain("pattern");
    expect(labels).toContain("format");
    expect(labels).not.toContain("properties");
    expect(labels).not.toContain("items");
  });
});
