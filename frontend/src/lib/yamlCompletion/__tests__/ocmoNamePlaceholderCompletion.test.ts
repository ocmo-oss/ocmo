import { describe, it, expect } from "vitest";
import { __testing } from "../yamlSchemaCompletion";
import type { ParameterCompletionOptions } from "../ocmoParameterCompletion";
import { textModel, makePosition, monacoStub } from "./monacoStub";
import { buildConfigEditorSchema } from "../../configEditorSchema";
import {
  OCMO_NAME_METADATA_SELECTORS,
  __testingOcmoNamePlaceholderCompletion,
  buildOcmoNameMetadataCompletions,
  shouldSuggestOcmoNameMetadata,
} from "../ocmoNamePlaceholderCompletion";

const metadataSchema = {
  type: "object",
  properties: {
    name: { type: "string" },
  },
};

const editorSchema = buildConfigEditorSchema("_ocmo", metadataSchema, {
  type: "object",
  properties: { foo: { type: "string" } },
});

const uriOptions = {
  namespace: "default",
  configPath: "apps/demo",
  metadataKey: "_ocmo",
};

function labels(items: Array<{ label: unknown }>): string[] {
  return items.map((item) =>
    typeof item.label === "string"
      ? item.label
      : ((item.label as { label?: string })?.label ?? String(item.label)),
  );
}

async function getSuggestions(
  yaml: string,
  lineNumber: number,
  column: number,
) {
  const model = textModel(yaml);
  const position = makePosition(lineNumber, column);
  return __testing.buildYamlCompletionSuggestions(
    monacoStub as never,
    editorSchema,
    model as never,
    position as never,
    uriOptions,
    { metadataKey: "_ocmo" },
  );
}

describe("ocmoNamePlaceholderCompletion", () => {
  it("suggests metadata selectors inside {._ocmo.}", async () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.}.yaml"'].join("\n");
    const line = yaml.split("\n")[1];
    const cursorCol = line.indexOf("}.");
    const items = await getSuggestions(yaml, 2, cursorCol);
    expect(labels(items)).toEqual(
      OCMO_NAME_METADATA_SELECTORS.map((s) => `._ocmo.${s.label}`),
    );
  });

  it("does not suggest when placeholder is complete", () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.Name}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}") + 1);
    expect(
      shouldSuggestOcmoNameMetadata(model as never, position as never),
    ).toBe(false);
  });

  it("does not suggest when typed text uniquely matches one selector", () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.Name}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}"));
    expect(
      shouldSuggestOcmoNameMetadata(model as never, position as never),
    ).toBe(false);
    expect(
      buildOcmoNameMetadataCompletions(
        monacoStub as never,
        model as never,
        position as never,
      ),
    ).toEqual([]);
  });

  it("still suggests when prefix matches only one incomplete selector", () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.N}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}"));
    expect(
      shouldSuggestOcmoNameMetadata(model as never, position as never),
    ).toBe(true);
    expect(
      labels(
        buildOcmoNameMetadataCompletions(
          monacoStub as never,
          model as never,
          position as never,
        ),
      ),
    ).toEqual(["._ocmo.Name"]);
  });

  it("still suggests when multiple selectors share the typed prefix", () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.Path}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}"));
    expect(
      shouldSuggestOcmoNameMetadata(model as never, position as never),
    ).toBe(true);
    expect(
      labels(
        buildOcmoNameMetadataCompletions(
          monacoStub as never,
          model as never,
          position as never,
        ),
      ),
    ).toEqual(["._ocmo.Path", "._ocmo.Path[-1]"]);
  });

  it("does not suggest for data placeholders", () => {
    const yaml = ["_ocmo:", '  name: "test{.database.}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}."));
    expect(
      shouldSuggestOcmoNameMetadata(model as never, position as never),
    ).toBe(false);
  });

  it("inserts metadata selector with correct range", () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}."));
    const items = buildOcmoNameMetadataCompletions(
      monacoStub as never,
      model as never,
      position as never,
    );
    const nameItem = items.find((item) => labels([item])[0] === "._ocmo.Name");
    expect(nameItem?.insertText).toBe("._ocmo.Name");
    expect(nameItem?.range).toMatchObject({
      startColumn: line.indexOf("{") + 2,
      endColumn: position.column,
    });
  });

  it("inserts full metadata path when only {. is typed", () => {
    const yaml = ["_ocmo:", '  name: "test{.}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("{.") + 2);
    const items = buildOcmoNameMetadataCompletions(
      monacoStub as never,
      model as never,
      position as never,
    );
    const nameItem = items.find((item) => labels([item])[0] === "._ocmo.Name");
    expect(nameItem?.insertText).toBe("._ocmo.Name");
  });

  it("keeps auto-trigger alive inside {._ocmo.} name placeholder", () => {
    const yaml = ["_ocmo:", '  name: "test{._ocmo.}.yaml"'].join("\n");
    const model = textModel(yaml);
    const line = yaml.split("\n")[1];
    const position = makePosition(2, line.indexOf("}."));
    const paramOptions: ParameterCompletionOptions = {
      metadataKey: "_ocmo",
    };
    expect(
      __testing.shouldAutoTriggerYamlSuggest(
        model as never,
        position as never,
        uriOptions,
        editorSchema,
        paramOptions,
      ),
    ).toBe(true);
  });

  it("detects placeholder partial at cursor", () => {
    expect(
      __testingOcmoNamePlaceholderCompletion.placeholderPartialAtCursor(
        "test{._ocmo.",
        "test{._ocmo.".length,
      ),
    ).toBe("._ocmo.");
    expect(
      __testingOcmoNamePlaceholderCompletion.placeholderPartialAtCursor(
        "test{.database.env}",
        "test{.database.".length,
      ),
    ).toBeNull();
  });
});
