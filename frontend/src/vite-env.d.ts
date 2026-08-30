/// <reference types="vite/client" />

declare module "*?raw" {
  const content: string;
  export default content;
}

declare module "monaco-editor/languages/definitions/yaml/yaml.js" {
  export const conf: import("monaco-editor").languages.LanguageConfiguration;
  export const language: import("monaco-editor").languages.IMonarchLanguage;
}
