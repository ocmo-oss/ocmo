/**
 * Monarch grammar for Jinja2 in Monaco Editor.
 * Adapted from the community contribution in microsoft/monaco-editor PR #4870 (MIT).
 */
import type * as Monaco from 'monaco-editor'

export const jinja2LanguageConfiguration: Monaco.languages.LanguageConfiguration = {
  comments: {
    blockComment: ['{#', '#}'],
  },
  brackets: [
    ['{%', '%}'],
    ['{{', '}}'],
    ['{#', '#}'],
    ['(', ')'],
    ['[', ']'],
    ['{', '}'],
  ],
  autoClosingPairs: [
    { open: '{#', close: ' #}' },
    { open: '{%', close: ' %}' },
    { open: '{{', close: ' }}' },
    { open: '[', close: ']' },
    { open: '(', close: ')' },
    { open: '{', close: '}' },
    { open: '"', close: '"', notIn: ['string', 'comment'] },
    { open: "'", close: "'", notIn: ['string', 'comment'] },
  ],
  surroundingPairs: [
    { open: '"', close: '"' },
    { open: "'", close: "'" },
    { open: '(', close: ')' },
    { open: '[', close: ']' },
    { open: '{', close: '}' },
    { open: '{%', close: '%}' },
    { open: '{{', close: '}}' },
    { open: '{#', close: '#}' },
  ],
  folding: {
    markers: {
      start: /^\s*({%\s*(block|filter|for|if|macro|raw))/,
      end: /^\s*({%\s*(endblock|endfilter|endfor|endif|endmacro|endraw)\s*%})/,
    },
  },
  indentationRules: {
    increaseIndentPattern:
      /^\s*({%\s*(block|filter|for|if|macro|raw|with|autoescape)\b(?!.*\b(endblock|endfilter|endfor|endif|endmacro|endraw|endwith|endautoescape))[^%]*%})/,
    decreaseIndentPattern:
      /^\s*({%\s*(elif|else|endblock|endfilter|endfor|endif|endmacro|endraw|endwith|endautoescape)\b.*?%})/,
  },
}

export const jinja2MonarchLanguage: Monaco.languages.IMonarchLanguage = {
  defaultToken: '',
  tokenPostfix: '.jinja',

  keywords: [
    'if', 'endif', 'for', 'endfor', 'block', 'endblock', 'extends', 'include', 'import', 'from',
    'as', 'recursive', 'macro', 'endmacro', 'call', 'endcall', 'filter', 'endfilter', 'set',
    'endset', 'raw', 'endraw', 'with', 'endwith', 'autoescape', 'endautoescape', 'scoped',
    'required', 'ignore', 'missing', 'context', 'trimmed', 'notrimmed', 'pluralize', 'continue',
    'break', 'do', 'and', 'or', 'not', 'in', 'is', 'else', 'elif',
  ],

  operators: ['+', '-', '*', '**', '/', '//', '%', '==', '<=', '>=', '<', '>', '!=', '=', '|', '~'],

  symbols: /[=><!~?&|+\-*/^%]+/,
  constants: ['true', 'false', 'none', 'True', 'False', 'None'],
  specialVars: ['loop', 'super', 'self', 'varargs', 'kwargs', 'caller'],
  escapes: /\\(?:[abfnrtv]|x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|N\{[a-zA-Z ]+\})/,

  tokenizer: {
    root: [
      [/\{#-+/, { token: 'comment.block', bracket: '@open', next: '@comment' }],
      [/\{#/, { token: 'comment.block', bracket: '@open', next: '@comment' }],
      [/\{\{-+/, { token: 'delimiter.variable', bracket: '@open', next: '@variable' }],
      [/\{\{/, { token: 'delimiter.variable', bracket: '@open', next: '@variable' }],
      [
        /(\{%\s*)(raw)(\s*%\})/,
        ['delimiter.tag', 'keyword.control', { token: 'delimiter.tag', next: '@rawblock' }],
      ],
      [
        /(\{%-?\s*)(raw)(\s*-?%\})/,
        ['delimiter.tag', 'keyword.control', { token: 'delimiter.tag', next: '@rawblock' }],
      ],
      [/\{%-+/, { token: 'delimiter.tag', bracket: '@open', next: '@block' }],
      [/\{%/, { token: 'delimiter.tag', bracket: '@open', next: '@block' }],
      [/[^\{]+/, ''],
      [/\{/, ''],
    ],

    comment: [
      [/-?#\}/, { token: 'comment.block', bracket: '@close', next: '@pop' }],
      [/[^#\}]+/, 'comment.block'],
      [/#|\}/, 'comment.block'],
    ],

    variable: [
      [/-?\}\}/, { token: 'delimiter.variable', bracket: '@close', next: '@pop' }],
      { include: '@expressionInside' },
    ],

    block: [
      [/-?%\}/, { token: 'delimiter.tag', bracket: '@close', next: '@pop' }],
      { include: '@expressionInside' },
    ],

    rawblock: [
      [
        /(\{%-?\s*)(endraw)(\s*-?%\})/,
        ['delimiter.tag', 'keyword.control', { token: 'delimiter.tag', next: '@pop' }],
      ],
      [/[^%]+/, 'comment.block.raw'],
      [/%/, 'comment.block.raw'],
    ],

    expressionInside: [
      [
        /\b[a-zA-Z_]\w*\b/,
        {
          cases: {
            '@keywords': 'keyword.control',
            '@constants': 'constant.language',
            '@specialVars': 'variable.language',
            '@default': 'variable.other',
          },
        },
      ],
      [/\d+(_\d+)*(\.\d+)?([eE][+\-]?\d+)?/, 'number'],
      [/"/, { token: 'string.quote.double', bracket: '@open', next: '@string_double' }],
      [/'/, { token: 'string.quote.single', bracket: '@open', next: '@string_single' }],
      [/\|(?=\s*[a-zA-Z_])/, { token: 'operators.filter', next: '@filterName' }],
      [
        /@symbols/,
        {
          cases: {
            '@operators': 'keyword.operator',
            '@default': 'delimiter',
          },
        },
      ],
      [/\./, 'delimiter.accessor'],
      [/[?:,()\[\]{}]/, 'delimiter'],
      [/\s+/, 'white'],
    ],

    string_double: [
      [/\\\\/, 'constant.character.escape'],
      [/\\"/, 'constant.character.escape'],
      [/@escapes/, 'constant.character.escape'],
      [/\\./, 'string.escape.invalid'],
      [/[^\\"]+/, 'string'],
      [/"/, { token: 'string.quote.double', bracket: '@close', next: '@pop' }],
    ],

    string_single: [
      [/\\\\/, 'constant.character.escape'],
      [/\\'/, 'constant.character.escape'],
      [/@escapes/, 'constant.character.escape'],
      [/\\./, 'string.escape.invalid'],
      [/[^\\']+/, 'string'],
      [/'/, { token: 'string.quote.single', bracket: '@close', next: '@pop' }],
    ],

    filterName: [
      [/\s+/, 'white'],
      [/[a-zA-Z_]\w*/, { token: 'variable.other.filter', next: '@pop' }],
      ['', { token: '', next: '@pop' }],
    ],
  },
}
