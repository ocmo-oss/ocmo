import { useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { treeApi } from "../../api/tree";
import { resolveApi } from "../../api/resolve";
import type { ResolveResponse } from "../../api/types";
import { pushApiError, pushNotification } from "../../store/notifications";
import { showToast } from "../ui/Toast";
import { hasOcmoRenderConfiguration } from "../../lib/ocmoMetadata";
import { validateDynamicParams } from "../../lib/resolveParameterValidation";
import { buildResolveQueryParams } from "../../lib/resolveQueryParams";
import {
  buildResolveCliCommand,
  buildResolveCurlCommand,
  buildResolveSdkCommand,
  type ResolveCommandConfig,
} from "../../lib/resolveCommands";
import { resolveActionLabel } from "../../lib/resolveTargetLabel";
import { env } from "../../env";
import { useConfigMetadataKey } from "../../store/health";

function buildResolveParams({
  versionRef,
  cast,
  markStable,
  noCreds,
  dynamicParams,
  castOptions,
  ignoreConfigsWithMissingTags,
}: {
  versionRef?: string;
  cast: string;
  markStable: boolean;
  noCreds: boolean;
  dynamicParams: Record<string, string>;
  castOptions: Record<string, string | boolean>;
  ignoreConfigsWithMissingTags?: boolean;
}) {
  return buildResolveQueryParams({
    versionRef,
    noCreds,
    dynamicParams,
    cast,
    markStable,
    castOptions,
    ignoreConfigsWithMissingTags,
  });
}

export function useResolveWorkflow({
  namespace,
  path,
  versionRef,
  content,
  isDirty = false,
  mode = "config",
}: {
  namespace: string;
  path: string;
  versionRef?: string;
  content?: string;
  isDirty?: boolean;
  mode?: "config" | "folder";
}) {
  const isFolder = mode === "folder";
  const useDraftResolve = !isFolder && isDirty;
  const configMetadataKey = useConfigMetadataKey();
  const castUnavailable = useMemo(
    () =>
      Boolean(
        content && hasOcmoRenderConfiguration(content, configMetadataKey),
      ),
    [content, configMetadataKey],
  );
  const [cast, setCast] = useState("");
  const [castOpen, setCastOpen] = useState(false);
  const [castOptions, setCastOptions] = useState<
    Record<string, string | boolean>
  >({});
  const [noCreds, setNoCreds] = useState(true);
  const [resolveMenuOpen, setResolveMenuOpen] = useState(false);
  const [dynamicParams, setDynamicParams] = useState<Record<string, string>>(
    {},
  );
  const [folderVersion, setFolderVersion] = useState("latest");
  const [ignoreMissingTags, setIgnoreMissingTags] = useState(false);
  const [resolveResult, setResolveResult] = useState<ResolveResponse | null>(
    null,
  );
  const [awaitingArtifacts, setAwaitingArtifacts] = useState(false);

  const effectiveVersionRef = isFolder ? folderVersion : versionRef;

  const paramQueryParams = useMemo(
    () =>
      buildResolveQueryParams({
        versionRef: effectiveVersionRef,
        noCreds,
        dynamicParams: {},
      }),
    [effectiveVersionRef, noCreds],
  );

  const {
    data: paramsData,
    isLoading: paramsLoading,
    isFetching: paramsFetching,
    isError: paramsIsError,
    error: paramsError,
  } = useQuery({
    queryKey: ["resolve-params", namespace, path, paramQueryParams],
    queryFn: ({ signal }) =>
      resolveApi.parameters(namespace, path, paramQueryParams, signal),
    staleTime: 0,
    placeholderData: keepPreviousData,
    enabled: !isFolder,
  });

  const { data: castFormatsData } = useQuery({
    queryKey: ["cast-formats"],
    queryFn: ({ signal }) => resolveApi.castFormats(signal),
    staleTime: 60_000,
    enabled: !castUnavailable,
  });

  const castSchema = useMemo(() => {
    if (!cast) return null;
    return (
      castFormatsData?.formats.find((f) => f.format === cast)?.options_schema ??
      null
    );
  }, [cast, castFormatsData]);

  useEffect(() => {
    setCastOptions({});
  }, [cast]);

  useEffect(() => {
    if (!castUnavailable) return;
    setCast("");
    setCastOptions({});
    setCastOpen(false);
  }, [castUnavailable]);

  useEffect(() => {
    if (!paramsData?.parameters) return;
    setDynamicParams((prev) => {
      const next = { ...prev };
      for (const [name, param] of Object.entries(paramsData.parameters)) {
        if (param.type === "dynamic" && next[name] === undefined) {
          next[name] =
            param.declared_default != null
              ? String(param.declared_default)
              : "";
        }
      }
      return next;
    });
  }, [paramsData]);

  const resolveMut = useMutation({
    mutationFn: (markStable: boolean) => {
      const params = buildResolveParams({
        versionRef: effectiveVersionRef,
        cast,
        markStable,
        noCreds,
        dynamicParams,
        castOptions,
        ignoreConfigsWithMissingTags: isFolder ? ignoreMissingTags : undefined,
      });
      if (useDraftResolve && content !== undefined) {
        return treeApi.resolveDraft(namespace, path, content, params);
      }
      return treeApi.resolve(namespace, path, params);
    },
    onSuccess: (result) => {
      setResolveResult(result);
      setAwaitingArtifacts(result.artifacts.length > 0);
      showToast(useDraftResolve ? "Draft resolved" : "Resolved successfully");
      setResolveMenuOpen(false);
    },
    onError: (e: Error) => {
      setAwaitingArtifacts(false);
      pushApiError("Resolve failed", e);
    },
  });

  const parameters = paramsData?.parameters ?? {};
  const paramEntries = Object.entries(parameters);
  const paramErrors = useMemo(
    () => validateDynamicParams(dynamicParams, parameters),
    [dynamicParams, parameters],
  );
  const hasParamErrors = Object.keys(paramErrors).length > 0;
  const showParamsLoading =
    !isFolder && (paramsLoading || paramsFetching) && !paramsData;
  const resolveLabel = resolveActionLabel(useDraftResolve, effectiveVersionRef);
  const resolveMarkStableLabel = resolveActionLabel(
    useDraftResolve,
    effectiveVersionRef,
    { markStable: true },
  );
  const resolveActive = resolveMut.isPending || awaitingArtifacts;

  const resolveCommandConfig = useMemo<ResolveCommandConfig>(
    () => ({
      namespace,
      path,
      mode,
      versionRef: effectiveVersionRef,
      noCreds,
      cast,
      castOptions,
      dynamicParams,
      ignoreConfigsWithMissingTags: isFolder ? ignoreMissingTags : undefined,
      isDraft: useDraftResolve,
      apiBase: env.apiBase,
    }),
    [
      namespace,
      path,
      mode,
      effectiveVersionRef,
      noCreds,
      cast,
      castOptions,
      dynamicParams,
      isFolder,
      ignoreMissingTags,
      useDraftResolve,
    ],
  );

  const copyResolveCommand = async (kind: "curl" | "cli" | "sdk") => {
    const text =
      kind === "curl"
        ? buildResolveCurlCommand(resolveCommandConfig)
        : kind === "cli"
          ? buildResolveCliCommand(resolveCommandConfig)
          : buildResolveSdkCommand(resolveCommandConfig);
    try {
      await navigator.clipboard.writeText(text);
      showToast(`Copied ${kind} command`);
      setResolveMenuOpen(false);
    } catch {
      pushNotification("error", "Copy failed");
    }
  };

  const clearArtifactsLoading = (loading: boolean) => {
    if (!loading) setAwaitingArtifacts(false);
  };

  return {
    isFolder,
    useDraftResolve,
    castUnavailable,
    cast,
    setCast,
    castOpen,
    setCastOpen,
    castOptions,
    setCastOptions,
    castSchema,
    noCreds,
    setNoCreds,
    resolveMenuOpen,
    setResolveMenuOpen,
    dynamicParams,
    setDynamicParams,
    folderVersion,
    setFolderVersion,
    ignoreMissingTags,
    setIgnoreMissingTags,
    resolveResult,
    effectiveVersionRef,
    paramEntries,
    paramErrors,
    hasParamErrors,
    showParamsLoading,
    paramsIsError,
    paramsError,
    paramsData,
    resolveLabel,
    resolveMarkStableLabel,
    resolveActive,
    resolveMut,
    copyResolveCommand,
    clearArtifactsLoading,
  };
}
