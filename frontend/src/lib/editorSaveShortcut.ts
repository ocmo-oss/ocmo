import type { editor } from 'monaco-editor'
import type * as Monaco from 'monaco-editor'

function isSaveKey(event: KeyboardEvent): boolean {
  if (!event.ctrlKey && !event.metaKey) return false
  return event.key.toLowerCase() === 's' || event.code === 'KeyS'
}

function isMonacoSaveShortcut(
  e: editor.IKeyboardEvent,
  monaco: typeof Monaco,
): boolean {
  if (!e.ctrlKey && !e.metaKey) return false
  if (e.keyCode === monaco.KeyCode.KeyS) return true
  return isSaveKey(e.browserEvent)
}

function editorHasFocus(editorInstance: editor.IStandaloneCodeEditor): boolean {
  return editorInstance.hasTextFocus() || editorInstance.hasWidgetFocus()
}

export function installEditorSaveShortcut(
  editorInstance: editor.IStandaloneCodeEditor,
  monaco: typeof Monaco,
  getOnPrepareSave: () => () => void,
): Monaco.IDisposable {
  let disposed = false

  const invoke = () => {
    if (disposed) return
    getOnPrepareSave()()
  }

  editorInstance.addCommand(
    monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
    () => {
      invoke()
    },
  )

  const monacoKeydownDisposable = editorInstance.onKeyDown(e => {
    if (disposed || !isMonacoSaveShortcut(e, monaco)) return
    e.preventDefault()
    e.stopPropagation()
    e.browserEvent.preventDefault()
    e.browserEvent.stopPropagation()
    invoke()
  })

  const onWindowKeyDown = (event: KeyboardEvent) => {
    if (disposed || !isSaveKey(event)) return
    if (!editorHasFocus(editorInstance)) return
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation()
    invoke()
  }

  window.addEventListener('keydown', onWindowKeyDown, true)

  return {
    dispose() {
      disposed = true
      monacoKeydownDisposable.dispose()
      window.removeEventListener('keydown', onWindowKeyDown, true)
    },
  }
}
