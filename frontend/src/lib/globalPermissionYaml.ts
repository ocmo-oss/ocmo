import { parse, stringify } from "yaml";
import type { GlobalPermissionRulePayload } from "../api/types";

export const NEW_GLOBAL_PERMISSION_RULE_TEMPLATE = `namespace: <pattern>
read:
  actors: []
write:
  actors: []
delete: 
  actors: []
`;

export function rulePayloadToYaml(rule: GlobalPermissionRulePayload): string {
  return stringify(rule, { lineWidth: 0 }).trimEnd();
}

export function parseRulePayloadYaml(
  source: string,
): GlobalPermissionRulePayload {
  const doc = parse(source);
  if (!doc || typeof doc !== "object" || Array.isArray(doc)) {
    throw new Error("Rule must be a YAML mapping");
  }
  return doc as GlobalPermissionRulePayload;
}
