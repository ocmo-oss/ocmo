import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchConfigDataSchema, fetchConfigMetadataSchema } from '../api/schema'
import { permissionsConfigPath } from '../lib/builtinPaths'
import { buildConfigEditorSchema, configEditorModelPath } from '../lib/configEditorSchema'
import { isJsonSchemaConfigContent } from '../lib/ocmoMetadata'
import { PERMISSIONS_POLICY_CONFIG_PATH } from '../lib/permissionSchema'
import { useConfigMetadataKey } from '../store/health'

interface UseConfigYamlSchemaOptions {
  namespace: string
  path: string
  versionRef?: string
  /** Live editor buffer; used to detect metadata `is_json_schema` before save. */
  editorContent?: string
  /** When false, only metadata-key autocomplete is available (unsaved new configs). */
  hasSavedVersion?: boolean
}

export function useConfigYamlSchema({
  namespace,
  path,
  versionRef,
  editorContent = '',
  hasSavedVersion = true,
}: UseConfigYamlSchemaOptions) {
  const configMetadataKey = useConfigMetadataKey()
  const modelPath = configEditorModelPath(namespace, path)
  const permissionsPolicyPath = permissionsConfigPath()
  const isPermissionsPolicyConfig = path === permissionsPolicyPath
    || path === PERMISSIONS_POLICY_CONFIG_PATH

  const metadataQuery = useQuery({
    queryKey: ['config-metadata-schema'],
    queryFn: ({ signal }) => fetchConfigMetadataSchema(signal),
    staleTime: Number.POSITIVE_INFINITY,
  })

  const isJsonSchemaMode = useMemo(
    () => isJsonSchemaConfigContent(editorContent, configMetadataKey),
    [editorContent, configMetadataKey],
  )

  const dataSchemaQuery = useQuery({
    queryKey: ['config-data-schema', namespace, path, versionRef ?? 'latest'],
    queryFn: ({ signal }) =>
      fetchConfigDataSchema(
        namespace,
        path,
        versionRef ? { version: versionRef } : undefined,
        signal,
      ),
    enabled: hasSavedVersion && (!isJsonSchemaMode || isPermissionsPolicyConfig),
  })

  const composedSchema = useMemo(() => {
    if (!metadataQuery.data || !configMetadataKey) {
      return null
    }
    const useExplicitDataSchema = isPermissionsPolicyConfig && Boolean(dataSchemaQuery.data)
    return buildConfigEditorSchema(
      configMetadataKey,
      metadataQuery.data,
      dataSchemaQuery.data ?? null,
      {
        isJsonSchemaMode: isJsonSchemaMode && !useExplicitDataSchema,
        useExplicitDataSchema,
      },
    )
  }, [
    configMetadataKey,
    metadataQuery.data,
    dataSchemaQuery.data,
    isJsonSchemaMode,
    isPermissionsPolicyConfig,
  ])

  return {
    modelPath,
    composedSchema,
    metadataKey: configMetadataKey,
    isJsonSchemaMode,
    isReady: Boolean(composedSchema),
  }
}
