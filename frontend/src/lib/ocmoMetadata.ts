import { parseDocument } from "yaml";
import { DEFAULT_CONFIG_METADATA_KEY } from "../store/health";

/** Whether the config YAML declares metadata `is_json_schema: true`. */
export function isJsonSchemaConfigContent(
  content: string,
  metadataKey = DEFAULT_CONFIG_METADATA_KEY,
): boolean {
  const block = extractOcmoMetadataBlock(content, metadataKey);
  if (!block) return false;
  return /^\s*is_json_schema:\s*true\s*$/m.test(block);
}

/** Whether the config YAML declares metadata `render` (cast is incompatible with render). */
export function hasOcmoRenderConfiguration(
  content: string,
  metadataKey = DEFAULT_CONFIG_METADATA_KEY,
): boolean {
  const block = extractOcmoMetadataBlock(content, metadataKey);
  if (!block) return false;
  return /^\s*render:\s*(\n|\S)/m.test(block);
}

function extractOcmoMetadataBlock(
  content: string,
  metadataKey: string,
): string | undefined {
  const escapedKey = metadataKey.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return content.match(
    new RegExp(
      `(?:^|\\n)\\s*${escapedKey}:\\s*\\n([\\s\\S]*?)(?=\\n\\S|\\s*$)`,
    ),
  )?.[1];
}

function readYamlMapping(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function extractNestedYamlBlock(
  parentBlock: string,
  key: string,
): string | undefined {
  const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const header = new RegExp(`^(\\s*)${escapedKey}:\\s*\\n`, "m");
  const headerMatch = header.exec(parentBlock);
  if (!headerMatch) return undefined;

  const indent = headerMatch[1];
  const bodyStart = headerMatch.index + headerMatch[0].length;
  const rest = parentBlock.slice(bodyStart);
  const escapedIndent = indent.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const siblingAt = rest.search(new RegExp(`^${escapedIndent}\\S`, "m"));
  return siblingAt === -1 ? rest : rest.slice(0, siblingAt);
}

/** Detect manual propagation configured in config YAML metadata section. */
export function hasManualPropagation(
  content: string,
  metadataKey = DEFAULT_CONFIG_METADATA_KEY,
): boolean {
  if (!content.trim()) return false;

  try {
    const root = readYamlMapping(
      parseDocument(content, { strict: false }).toJS(),
    );
    const metadata = root ? readYamlMapping(root[metadataKey]) : null;
    const propagation = metadata ? readYamlMapping(metadata.propagation) : null;
    if (propagation) {
      return propagation.enabled === true && propagation.trigger === "manual";
    }
  } catch {
    // Fall back to text scan when the editor buffer is not valid YAML yet.
  }

  const block = extractOcmoMetadataBlock(content, metadataKey);
  if (!block) return false;

  const propagation = extractNestedYamlBlock(block, "propagation");
  if (!propagation) return false;

  const enabled = /^\s*enabled:\s*true\b/m.test(propagation);
  const manual = /^\s*trigger:\s*manual\b/m.test(propagation);
  return enabled && manual;
}
