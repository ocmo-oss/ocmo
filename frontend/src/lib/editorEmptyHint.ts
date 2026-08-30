import type { editor } from "monaco-editor";
import type * as Monaco from "monaco-editor";

function isDocumentEmpty(model: editor.ITextModel | null): boolean {
  return !model || model.getValue().trim() === "";
}

function isSuggestWidgetVisible(
  editorInstance: editor.IStandaloneCodeEditor,
): boolean {
  const suggest = editorInstance.getDomNode()?.querySelector(".suggest-widget");
  return suggest?.classList.contains("visible") ?? false;
}

export interface EditorEmptyHintOptions {
  text: string;
  /** When false the hint is never shown. */
  enabled?: () => boolean;
}

export function installEditorEmptyHint(
  editorInstance: editor.IStandaloneCodeEditor,
  monaco: typeof Monaco,
  options: EditorEmptyHintOptions,
): Monaco.IDisposable & { refresh: () => void } {
  const domNode = document.createElement("div");
  domNode.className = "editor-empty-hint";
  domNode.textContent = options.text;
  domNode.setAttribute("aria-hidden", "true");

  const widget: editor.IContentWidget = {
    getId: () => "editor.emptyHint",
    getDomNode: () => domNode,
    getPosition: () => {
      if (!shouldShow()) return null;
      return {
        position: { lineNumber: 1, column: 1 },
        preference: [monaco.editor.ContentWidgetPositionPreference.EXACT],
      };
    },
  };

  let widgetAdded = false;
  let observer: MutationObserver | null = null;

  const isEnabled = () => options.enabled?.() ?? true;

  const shouldShow = () => {
    if (editorInstance.getOption(monaco.editor.EditorOption.readOnly))
      return false;
    if (!isEnabled()) return false;
    if (!editorInstance.hasTextFocus()) return false;
    if (!isDocumentEmpty(editorInstance.getModel())) return false;
    return !isSuggestWidgetVisible(editorInstance);
  };

  const update = () => {
    if (!widgetAdded) {
      editorInstance.addContentWidget(widget);
      widgetAdded = true;
    }
    editorInstance.layoutContentWidget(widget);

    if (shouldShow() && !observer) {
      const root = editorInstance.getDomNode();
      if (!root) return;
      observer = new MutationObserver(() => update());
      observer.observe(root, {
        subtree: true,
        attributes: true,
        attributeFilter: ["class"],
      });
      return;
    }

    if (!shouldShow() && observer) {
      observer.disconnect();
      observer = null;
    }
  };

  const disposables = [
    editorInstance.onDidFocusEditorText(update),
    editorInstance.onDidBlurEditorText(update),
    editorInstance.onDidChangeModelContent(update),
    editorInstance.onDidChangeCursorPosition(update),
    editorInstance.onDidChangeConfiguration((e) => {
      if (e.hasChanged(monaco.editor.EditorOption.readOnly)) {
        update();
      }
    }),
  ];

  update();

  return {
    refresh: update,
    dispose() {
      for (const disposable of disposables) {
        disposable.dispose();
      }
      observer?.disconnect();
      observer = null;
      if (widgetAdded) {
        editorInstance.removeContentWidget(widget);
        widgetAdded = false;
      }
    },
  };
}
