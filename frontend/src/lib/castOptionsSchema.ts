export interface JsonSchemaProperty {
  type?: string | string[];
  title?: string;
  description?: string;
  enum?: unknown[];
  anyOf?: Array<{ const?: unknown; type?: string; enum?: unknown[] }>;
  default?: unknown;
  examples?: unknown[];
  minimum?: number;
  maximum?: number;
  "x-ocmo-incompatible-with"?: string[];
  "x-ocmo-enabled-when"?: Record<string, string>;
}

export function castOptionFieldLabel(
  key: string,
  prop: JsonSchemaProperty,
): string {
  if (prop.title?.trim()) return prop.title.trim();
  return key.replace(/_/g, " ");
}

export function castOptionEnumValues(
  prop: JsonSchemaProperty,
): unknown[] | null {
  if (prop.enum?.length) return prop.enum;

  const fromAnyOf = prop.anyOf?.flatMap((item) => {
    if (item.enum?.length) return item.enum;
    if (item.const !== undefined) return [item.const];
    return [];
  });
  if (fromAnyOf?.length) return fromAnyOf;

  return null;
}

export function castOptionFieldType(prop: JsonSchemaProperty): string {
  if (Array.isArray(prop.type)) {
    return prop.type.find((type) => type !== "null") ?? "string";
  }
  if (prop.type) return prop.type;
  if (prop.anyOf?.some((item) => item.type === "boolean")) return "boolean";
  if (prop.anyOf?.some((item) => item.type === "integer")) return "integer";
  if (prop.anyOf?.some((item) => item.type === "number")) return "number";
  return "string";
}

export function castOptionPlaceholder(
  prop: JsonSchemaProperty,
): string | undefined {
  if (
    prop.default !== undefined &&
    prop.default !== null &&
    prop.default !== ""
  ) {
    return String(prop.default);
  }
  const example = prop.examples?.find(
    (value) => value !== undefined && value !== null && value !== "",
  );
  if (example !== undefined) return String(example);
  return undefined;
}

export function formatCastOptionDefault(
  prop: JsonSchemaProperty,
): string | undefined {
  if (prop.default === undefined) return undefined;
  if (prop.default === null) return "null (auto)";
  if (typeof prop.default === "boolean") return prop.default ? "true" : "false";
  if (prop.default === "") return "empty";
  return String(prop.default);
}
