import { useTheme } from '../store/theme'
import { monacoEditorTheme } from '../lib/monacoTheme'

export function useMonacoEditorTheme(): string {
  const { theme } = useTheme()
  return monacoEditorTheme(theme)
}
