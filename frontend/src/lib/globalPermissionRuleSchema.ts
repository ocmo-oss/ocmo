import type { JsonSchemaDocument } from "../api/schema";

function claimExampleValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return null;
  }
}

/** JSON Schema for a single global permission rule (YAML editor autocomplete). */
export const globalPermissionRuleSchema: JsonSchemaDocument = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  title: "Global permission rule",
  description:
    "Namespace-scoped gate evaluated in list order. First matching rule wins for each operation.",
  type: "object",
  additionalProperties: false,
  required: ["namespace"],
  properties: {
    id: {
      type: "string",
      minLength: 1,
      maxLength: 200,
      description: "Optional stable identifier for audits and documentation.",
    },
    description: {
      type: "string",
      maxLength: 500,
      description: "Human-readable summary of what this rule grants.",
    },
    namespace: {
      type: "string",
      minLength: 1,
      maxLength: 200,
      description:
        "Namespace name glob pattern (fnmatch). Use * to match any namespace.",
    },
    read: { $ref: "#/$defs/gate" },
    write: { $ref: "#/$defs/gate" },
    delete: { $ref: "#/$defs/gate" },
    audit: { $ref: "#/$defs/gate" },
  },
  $defs: {
    gate: {
      type: "object",
      additionalProperties: false,
      required: ["actors"],
      properties: {
        actors: {
          type: "array",
          description: "Users matching any actor entry are granted this gate.",
          items: { $ref: "#/$defs/actor" },
        },
      },
    },
    actor: {
      type: "object",
      additionalProperties: false,
      required: ["kind", "claims"],
      properties: {
        kind: {
          const: "User",
          description: "Match authenticated human users.",
        },
        claims: {
          type: "object",
          minProperties: 1,
          description: "OIDC claim names mapped to literal values or *.",
          additionalProperties: {
            type: "string",
            minLength: 1,
          },
        },
      },
    },
  },
};

/** Build schema with claim-key suggestions from the signed-in user's OIDC claims. */
export function buildGlobalPermissionRuleSchema(
  userClaims?: Record<string, unknown> | null,
): JsonSchemaDocument {
  const claimExample: Record<string, string> = {};
  if (userClaims) {
    for (const [key, value] of Object.entries(userClaims).sort(([a], [b]) =>
      a.localeCompare(b),
    )) {
      const exampleValue = claimExampleValue(value);
      if (exampleValue !== null) {
        claimExample[key] = exampleValue;
      }
    }
  }

  const defs = globalPermissionRuleSchema.$defs as
    Record<string, JsonSchemaDocument> | undefined;
  const actor = defs?.actor;
  const actorProperties = actor?.properties as
    Record<string, JsonSchemaDocument> | undefined;
  const claims = actorProperties?.claims;
  if (!actor || !claims || !defs || Object.keys(claimExample).length === 0) {
    return globalPermissionRuleSchema;
  }

  return {
    ...globalPermissionRuleSchema,
    $defs: {
      ...defs,
      actor: {
        ...actor,
        properties: {
          ...actorProperties,
          claims: {
            ...claims,
            examples: [claimExample],
          },
        },
      },
    },
  };
}
