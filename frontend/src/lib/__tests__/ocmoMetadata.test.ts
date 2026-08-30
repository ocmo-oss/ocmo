import { describe, expect, it } from "vitest";
import {
  hasManualPropagation,
  hasOcmoRenderConfiguration,
  isJsonSchemaConfigContent,
} from "../ocmoMetadata";

describe("isJsonSchemaConfigContent", () => {
  it("returns true when _ocmo declares is_json_schema: true", () => {
    const content = `_ocmo:
  is_json_schema: true
type: object
`;
    expect(isJsonSchemaConfigContent(content)).toBe(true);
  });

  it("returns false when is_json_schema is absent", () => {
    const content = `_ocmo:
  extend:
    configs:
      - base@latest
foo: bar
`;
    expect(isJsonSchemaConfigContent(content)).toBe(false);
  });

  it("returns false when is_json_schema is false", () => {
    const content = `_ocmo:
  is_json_schema: false
`;
    expect(isJsonSchemaConfigContent(content)).toBe(false);
  });

  it("respects custom metadata key", () => {
    const content = `meta:
  is_json_schema: true
`;
    expect(isJsonSchemaConfigContent(content, "meta")).toBe(true);
    expect(isJsonSchemaConfigContent(content, "_ocmo")).toBe(false);
  });
});

describe("hasOcmoRenderConfiguration", () => {
  it("returns true when render templates are declared", () => {
    const content = `_ocmo:
  render:
    mode: distribute
    templates:
      - shared/tmpl@latest
key: value
`;
    expect(hasOcmoRenderConfiguration(content)).toBe(true);
  });

  it("returns false when render is absent", () => {
    const content = `_ocmo:
  cast:
    format: json
foo: bar
`;
    expect(hasOcmoRenderConfiguration(content)).toBe(false);
  });

  it("detects render in draft content with other metadata", () => {
    const content = `_ocmo:
  parameters:
    env:
      type: projected
      value: .Path[-1]
  render:
    templates:
      - tmpl@latest
`;
    expect(hasOcmoRenderConfiguration(content)).toBe(true);
  });
});

describe("hasManualPropagation", () => {
  it("returns true when manual propagation is enabled", () => {
    const content = `_ocmo:
  propagation:
    enabled: true
    trigger: manual
    targets:
      - other/config@latest
foo: bar
`;
    expect(hasManualPropagation(content)).toBe(true);
  });

  it("returns false when trigger is not manual", () => {
    const content = `_ocmo:
  propagation:
    enabled: true
    trigger: tag
    tag: stable
`;
    expect(hasManualPropagation(content)).toBe(false);
  });

  it("returns false when propagation is disabled", () => {
    const content = `_ocmo:
  propagation:
    enabled: false
    trigger: manual
`;
    expect(hasManualPropagation(content)).toBe(false);
  });

  it("returns false when propagation is absent", () => {
    const content = `_ocmo:
  cast:
    format: json
foo: bar
`;
    expect(hasManualPropagation(content)).toBe(false);
  });

  it("respects custom metadata key", () => {
    const content = `meta:
  propagation:
    enabled: true
    trigger: manual
`;
    expect(hasManualPropagation(content, "meta")).toBe(true);
    expect(hasManualPropagation(content, "_ocmo")).toBe(false);
  });

  it("detects manual propagation in a realistic multi-section config", () => {
    const content = `_ocmo:
  propagation:
    enabled: true
    trigger: manual
    mode: data
    targets:
      - propagate/qa/app/config
      - propagate/stage/app/config@latest
      - propagate/perf/app/config
    exclude:
      - logging.level
      - some.dev.specific.conf
environment: dev
app:
  name: my-service
  replicas: 1
database:
  host: db.dev.example.com
  port: 5432
  name: myapp_dev
logging:
  level: trace
  format: json
some:
  dev:
    specific:
      conf: should-not-reach-perf
feature_flags:
  new_ui: true
`;
    expect(hasManualPropagation(content)).toBe(true);
  });

  it("falls back to text scan for draft YAML with manual propagation", () => {
    const content = `_ocmo:
  propagation:
    enabled: true
    trigger: manual
    targets:
      - propagate/qa/app/config
environment: dev
app:
  name: my-service
  replicas: 1
`;
    expect(hasManualPropagation(content)).toBe(true);
  });
});
