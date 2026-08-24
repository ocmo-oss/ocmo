import { describe, expect, it } from 'vitest'
import { applyMarkdownAction } from '../markdownEditorActions'

describe('applyMarkdownAction', () => {
  it('wraps selection in bold markers', () => {
    const result = applyMarkdownAction('hello world', 6, 11, 'bold')
    expect(result.value).toBe('hello **world**')
    expect(result.selectionStart).toBe(8)
    expect(result.selectionEnd).toBe(13)
  })

  it('inserts bold placeholder with collapsed caret when nothing is selected', () => {
    const result = applyMarkdownAction('hello', 5, 5, 'bold')
    expect(result.value).toBe('hello**text**')
    expect(result.selectionStart).toBe(7)
    expect(result.selectionEnd).toBe(7)
  })

  it('prefixes lines with heading markers', () => {
    const result = applyMarkdownAction('one\ntwo', 0, 7, 'heading')
    expect(result.value).toBe('## one\n## two')
  })

  it('inserts a link with url selection when text is selected', () => {
    const result = applyMarkdownAction('click here', 0, 5, 'link')
    expect(result.value).toBe('[click](url) here')
    expect(result.selectionStart).toBe(8)
    expect(result.selectionEnd).toBe(11)
  })

  it('inserts a link with collapsed caret on url when nothing is selected', () => {
    const result = applyMarkdownAction('hello', 5, 5, 'link')
    expect(result.value).toBe('hello[text](url)')
    expect(result.selectionStart).toBe(12)
    expect(result.selectionEnd).toBe(12)
  })

  it('inserts an empty code block at the cursor', () => {
    const result = applyMarkdownAction('line', 4, 4, 'codeBlock')
    expect(result.value).toBe('line```\n\n```')
    expect(result.selectionStart).toBe(8)
    expect(result.selectionEnd).toBe(8)
  })

  it('wraps single-line selection in a code block', () => {
    const result = applyMarkdownAction('hello world', 6, 11, 'codeBlock')
    expect(result.value).toBe('hello ```\nworld\n```')
    expect(result.selectionStart).toBe(10)
    expect(result.selectionEnd).toBe(15)
  })

  it('numbers list lines', () => {
    const result = applyMarkdownAction('a\nb', 0, 3, 'ol')
    expect(result.value).toBe('1. a\n2. b')
  })

  it('prefixes the current line as heading without a selection', () => {
    const result = applyMarkdownAction('hello', 5, 5, 'heading')
    expect(result.value).toBe('## hello')
    expect(result.selectionStart).toBe(8)
    expect(result.selectionEnd).toBe(8)
  })

  it('prefixes an empty document as heading without a selection', () => {
    const result = applyMarkdownAction('', 0, 0, 'heading')
    expect(result.value).toBe('## ')
    expect(result.selectionStart).toBe(3)
    expect(result.selectionEnd).toBe(3)
  })

  it('prefixes an empty line without a selection', () => {
    const result = applyMarkdownAction('hello\n\nworld', 6, 6, 'heading')
    expect(result.value).toBe('hello\n## \nworld')
    expect(result.selectionStart).toBe(9)
    expect(result.selectionEnd).toBe(9)
  })

  it('prefixes the current line as a bullet list without a selection', () => {
    const result = applyMarkdownAction('item', 4, 4, 'ul')
    expect(result.value).toBe('- item')
  })

  it('prefixes the current line as a quote without a selection', () => {
    const result = applyMarkdownAction('note', 4, 4, 'quote')
    expect(result.value).toBe('> note')
  })
})
