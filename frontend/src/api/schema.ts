import { api, ApiError } from "./client";

export type JsonSchemaDocument = Record<string, unknown>;

export function fetchConfigMetadataSchema(
  signal?: AbortSignal,
): Promise<JsonSchemaDocument> {
  return api.get<JsonSchemaDocument>("/~config-metadata-schema", { signal });
}

export function fetchResolverConfigurationSchema(
  signal?: AbortSignal,
): Promise<JsonSchemaDocument> {
  return api.get<JsonSchemaDocument>("/~resolver-configuration-schema", {
    signal,
  });
}

export async function fetchConfigDataSchema(
  namespace: string,
  path: string,
  params?: { version?: string },
  signal?: AbortSignal,
): Promise<JsonSchemaDocument | null> {
  try {
    return await api.get<JsonSchemaDocument>(
      `/ns/${namespace}/~config-schema/${path}`,
      { params, signal },
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
