import { DiffEditor } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { useCallback, useEffect, useRef } from "react";
import type { CrLineRange } from "../../lib/changeRequestLineRefs";
import { useConfigYamlSchema } from "../../hooks/useConfigYamlSchema";
import { configEditorModelPath } from "../../lib/configEditorSchema";
import { useMonacoEditorTheme } from "../../hooks/useMonacoEditorTheme";
import { defineMonacoThemes } from "../../lib/monacoTheme";
import {
  installYamlCompletionTriggers,
  registerYamlSchemaCompletion,
} from "../../lib/yamlCompletion";
import { yamlEditorOptions } from "../../lib/yamlEditorOptions";
import "./changeRequestDiffEditor.css";

export const CHANGE_REQUEST_EDITOR_HEIGHT = "min(42vh, 400px)";

type ChangeRequestDiffEditorProps = {
  original: string;
  modified: string;
  language: string;
  readOnly: boolean;
  onModifiedChange: (value: string) => void;
  className?: string;
  height?: string;
  namespace?: string;
  configPath?: string;
  enableYamlCompletion?: boolean;
  editorContent?: string;
  highlightLineRange?: CrLineRange | null;
  onModifiedEditorMount?: (
    editorInstance: editor.IStandaloneCodeEditor,
    monaco: typeof import("monaco-editor"),
  ) => void;
};

const diffEditorLayoutOptions = {
  renderMarginRevertIcon: false,
  renderGutterMenu: false,
  glyphMargin: false,
  lightbulb: { enabled: "off" as editor.ShowLightbulbIconMode },
  lineDecorationsWidth: 28,
  lineNumbersMinChars: 3,
  folding: false,
} as const;

export function ChangeRequestDiffEditor({
  original,
  modified,
  language,
  readOnly,
  onModifiedChange,
  className,
  height = CHANGE_REQUEST_EDITOR_HEIGHT,
  namespace,
  configPath,
  enableYamlCompletion = false,
  editorContent = "",
  highlightLineRange = null,
  onModifiedEditorMount,
}: ChangeRequestDiffEditorProps) {
  const theme = useMonacoEditorTheme();
  const diffRef = useRef<editor.IStandaloneDiffEditor | null>(null);
  const monacoRef = useRef<typeof import("monaco-editor") | null>(null);
  const modifiedEditorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const onChangeRef = useRef(onModifiedChange);
  onChangeRef.current = onModifiedChange;
  const onModifiedEditorMountRef = useRef(onModifiedEditorMount);
  onModifiedEditorMountRef.current = onModifiedEditorMount;

  const completionDisposableRef = useRef<
    import("monaco-editor").IDisposable | null
  >(null);
  const suggestTriggerDisposableRef = useRef<
    import("monaco-editor").IDisposable | null
  >(null);
  const lineHighlightRef = useRef<editor.IEditorDecorationsCollection | null>(
    null,
  );

  const { composedSchema, metadataKey: configMetadataKey } =
    useConfigYamlSchema({
      namespace: namespace ?? "",
      path: configPath ?? "",
      editorContent,
      hasSavedVersion: true,
    });
  const composedSchemaRef = useRef(composedSchema);
  composedSchemaRef.current = composedSchema;
  const metadataKeyRef = useRef(configMetadataKey);
  metadataKeyRef.current = configMetadataKey;

  const modelPath =
    namespace && configPath
      ? configEditorModelPath(namespace, configPath)
      : undefined;

  const attachCompletion = useCallback(
    (
      monaco: typeof import("monaco-editor"),
      modifiedEditor: editor.IStandaloneCodeEditor,
    ) => {
      if (!enableYamlCompletion || language !== "yaml") return;
      completionDisposableRef.current?.dispose();
      suggestTriggerDisposableRef.current?.dispose();
      if (!composedSchemaRef.current) return;

      const getUriReference = () => {
        const metadataKey = metadataKeyRef.current;
        if (!metadataKey || !namespace || !configPath) return null;
        return {
          namespace,
          configPath,
          metadataKey,
          allowOutsideMetadata:
            configPath === "_permissions" || configPath === "_webhooks",
        };
      };
      const getParameterCompletion = () => {
        const metadataKey = metadataKeyRef.current;
        if (!metadataKey) return null;
        return { metadataKey };
      };

      completionDisposableRef.current = registerYamlSchemaCompletion(
        monaco,
        () => composedSchemaRef.current,
        modifiedEditor,
        getUriReference,
        getParameterCompletion,
      );
      suggestTriggerDisposableRef.current = installYamlCompletionTriggers(
        modifiedEditor,
        monaco,
        () => composedSchemaRef.current,
        getUriReference,
        getParameterCompletion,
      );
    },
    [enableYamlCompletion, language, namespace, configPath],
  );

  useEffect(() => {
    const monaco = monacoRef.current;
    const modifiedEditor = modifiedEditorRef.current;
    if (monaco && modifiedEditor) {
      attachCompletion(monaco, modifiedEditor);
    }
  }, [attachCompletion, composedSchema]);

  useEffect(
    () => () => {
      completionDisposableRef.current?.dispose();
      suggestTriggerDisposableRef.current?.dispose();
    },
    [],
  );

  const handleMount = useCallback(
    (
      diff: editor.IStandaloneDiffEditor,
      monaco: typeof import("monaco-editor"),
    ) => {
      diffRef.current = diff;
      monacoRef.current = monaco;
      diff.updateOptions(diffEditorLayoutOptions);
      const editorOptions = {
        ...diffEditorLayoutOptions,
        lightbulb: { enabled: "off" as editor.ShowLightbulbIconMode },
      };
      diff.getOriginalEditor().updateOptions(editorOptions);
      const modifiedEditor = diff.getModifiedEditor();
      modifiedEditorRef.current = modifiedEditor;
      modifiedEditor.updateOptions(editorOptions);
      modifiedEditor.onDidChangeModelContent(() => {
        onChangeRef.current(modifiedEditor.getValue());
      });
      attachCompletion(monaco, modifiedEditor);
      onModifiedEditorMountRef.current?.(modifiedEditor, monaco);
    },
    [attachCompletion],
  );

  useEffect(() => {
    if (readOnly) return;
    const modifiedEditor = modifiedEditorRef.current;
    const monaco = monacoRef.current;
    if (!modifiedEditor || !monaco) return;
    onModifiedEditorMountRef.current?.(modifiedEditor, monaco);
  }, [readOnly, onModifiedEditorMount]);

  useEffect(() => {
    const diff = diffRef.current;
    if (!diff) return;
    const modifiedEditor = diff.getModifiedEditor();
    const model = modifiedEditor.getModel();
    if (model && model.getValue() !== modified) {
      modifiedEditor.setValue(modified);
    }
  }, [modified]);

  useEffect(() => {
    const modifiedEditor = modifiedEditorRef.current;
    const monaco = monacoRef.current;
    lineHighlightRef.current?.clear();
    lineHighlightRef.current = null;
    if (!modifiedEditor || !monaco || !highlightLineRange) return;

    lineHighlightRef.current = modifiedEditor.createDecorationsCollection([
      {
        range: new monaco.Range(
          highlightLineRange.start,
          1,
          highlightLineRange.end,
          1,
        ),
        options: {
          isWholeLine: true,
          className: "cr-line-highlight",
        },
      },
    ]);
    modifiedEditor.revealLineInCenter(highlightLineRange.start);
  }, [highlightLineRange, modified, original]);

  useEffect(
    () => () => {
      lineHighlightRef.current?.clear();
    },
    [],
  );

  return (
    <div className={`change-request-diff-editor ${className ?? ""}`}>
      <DiffEditor
        height={height}
        language={language}
        original={original}
        modified={modified}
        modifiedLanguage={language}
        modifiedModelPath={modelPath}
        theme={theme}
        onMount={handleMount}
        beforeMount={(monaco) => defineMonacoThemes(monaco)}
        options={{
          ...yamlEditorOptions(readOnly),
          ...diffEditorLayoutOptions,
          renderSideBySide: false,
          readOnly,
          originalEditable: false,
          enableSplitViewResizing: false,
          renderOverviewRuler: false,
          renderIndicators: true,
          diffAlgorithm: "advanced",
        }}
      />
    </div>
  );
}
