/**
 * Configure @monaco-editor/react to use the locally bundled monaco-editor
 * instead of loading it from the jsDelivr CDN.
 *
 * Worker setup lives in monacoEnvironment.ts (imported before this module).
 * Import this module once before any Monaco editor is rendered (main.tsx).
 *
 * Use the loader re-exported from @monaco-editor/react so Vite resolves the
 * same singleton @monaco-editor/loader instance the Editor component uses.
 */
import { loader } from '@monaco-editor/react'
import * as monaco from 'monaco-editor'
import { conf as yamlConf, language as yamlLanguage } from 'monaco-editor/languages/definitions/yaml/yaml.js'
import { jinja2LanguageConfiguration, jinja2MonarchLanguage } from './jinja2Language'
import { defineMonacoThemes } from './monacoTheme'

// Eagerly wire YAML instead of Monaco's lazy import('./yaml.js'), which Vite
// pre-bundles into node_modules/.vite/deps and can 504 as "Outdated Optimize Dep".
monaco.languages.setMonarchTokensProvider('yaml', yamlLanguage)
monaco.languages.setLanguageConfiguration('yaml', yamlConf)

monaco.languages.register({
  id: 'jinja2',
  extensions: ['.j2', '.jinja', '.jinja2'],
  aliases: ['Jinja2', 'jinja', 'jinja2'],
  mimetypes: ['text/x-jinja2'],
})
monaco.languages.setMonarchTokensProvider('jinja2', jinja2MonarchLanguage)
monaco.languages.setLanguageConfiguration('jinja2', jinja2LanguageConfiguration)

defineMonacoThemes(monaco)

loader.config({ monaco })
