import { useLayoutEffect, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import {
  Bold,
  Code,
  Code2,
  Eye,
  EyeOff,
  Heading2,
  Italic,
  Link,
  List,
  ListOrdered,
  Minus,
  Quote,
  Strikethrough,
} from 'lucide-react'
import {
  applyMarkdownAction,
  matchMarkdownShortcut,
  type MarkdownAction,
} from '../../lib/markdownEditorActions'
import { DescriptionMarkdown } from './DescriptionMarkdown'
import { cn } from './cn'

interface ToolbarAction {
  action: MarkdownAction
  icon: ReactNode
  label: string
  shortcut?: string
}

const TOOLBAR_ACTIONS: ToolbarAction[] = [
  { action: 'bold', icon: <Bold className="h-3.5 w-3.5" />, label: 'Bold', shortcut: 'Ctrl+B' },
  { action: 'italic', icon: <Italic className="h-3.5 w-3.5" />, label: 'Italic', shortcut: 'Ctrl+I' },
  { action: 'strike', icon: <Strikethrough className="h-3.5 w-3.5" />, label: 'Strikethrough', shortcut: 'Ctrl+Shift+X' },
  { action: 'heading', icon: <Heading2 className="h-3.5 w-3.5" />, label: 'Heading' },
  { action: 'link', icon: <Link className="h-3.5 w-3.5" />, label: 'Link', shortcut: 'Ctrl+K' },
  { action: 'ul', icon: <List className="h-3.5 w-3.5" />, label: 'Bullet list', shortcut: 'Ctrl+Shift+8' },
  { action: 'ol', icon: <ListOrdered className="h-3.5 w-3.5" />, label: 'Numbered list', shortcut: 'Ctrl+Shift+7' },
  { action: 'code', icon: <Code className="h-3.5 w-3.5" />, label: 'Inline code', shortcut: 'Ctrl+E' },
  { action: 'codeBlock', icon: <Code2 className="h-3.5 w-3.5" />, label: 'Code block' },
  { action: 'quote', icon: <Quote className="h-3.5 w-3.5" />, label: 'Quote' },
  { action: 'hr', icon: <Minus className="h-3.5 w-3.5" />, label: 'Horizontal rule' },
]

interface MarkdownEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows?: number
  className?: string
  textareaClassName?: string
  previewClassName?: string
  contentClassName?: string
  disabled?: boolean
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder = 'Write a Markdown description…',
  rows = 5,
  className,
  textareaClassName,
  previewClassName,
  contentClassName,
  disabled = false,
}: MarkdownEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const pendingSelection = useRef<{ start: number; end: number } | null>(null)
  const [preview, setPreview] = useState(false)
  const [history, setHistory] = useState<string[]>([value])
  const [historyIndex, setHistoryIndex] = useState(0)
  const lastExternalValue = useRef(value)

  useLayoutEffect(() => {
    if (value !== lastExternalValue.current) {
      lastExternalValue.current = value
      setHistory([value])
      setHistoryIndex(0)
    }
  }, [value])

  useLayoutEffect(() => {
    if (!pendingSelection.current || !textareaRef.current) return
    const { start, end } = pendingSelection.current
    textareaRef.current.focus()
    textareaRef.current.setSelectionRange(start, end)
    pendingSelection.current = null
  }, [value])

  const commitChange = (newValue: string, selection?: { start: number; end: number }) => {
    if (newValue === value) return

    const nextHistory = history.slice(0, historyIndex + 1)
    nextHistory.push(newValue)
    setHistory(nextHistory)
    setHistoryIndex(nextHistory.length - 1)
    lastExternalValue.current = newValue
    onChange(newValue)

    if (selection) {
      pendingSelection.current = selection
    }
  }

  const undo = () => {
    if (historyIndex <= 0) return
    const nextIndex = historyIndex - 1
    const nextValue = history[nextIndex]
    setHistoryIndex(nextIndex)
    lastExternalValue.current = nextValue
    onChange(nextValue)
  }

  const redo = () => {
    if (historyIndex >= history.length - 1) return
    const nextIndex = historyIndex + 1
    const nextValue = history[nextIndex]
    setHistoryIndex(nextIndex)
    lastExternalValue.current = nextValue
    onChange(nextValue)
  }

  const applyAction = (action: MarkdownAction) => {
    const el = textareaRef.current
    if (!el || disabled) return
    const result = applyMarkdownAction(value, el.selectionStart, el.selectionEnd, action)
    commitChange(result.value, { start: result.selectionStart, end: result.selectionEnd })
  }

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    commitChange(event.target.value)
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const mod = event.metaKey || event.ctrlKey

    if (mod && event.key.toLowerCase() === 'z' && !event.shiftKey) {
      event.preventDefault()
      undo()
      return
    }

    if (mod && (event.key.toLowerCase() === 'y' || (event.key.toLowerCase() === 'z' && event.shiftKey))) {
      event.preventDefault()
      redo()
      return
    }

    const action = matchMarkdownShortcut(event.nativeEvent)
    if (!action) return
    event.preventDefault()
    applyAction(action)
  }

  const panelClass = cn('item-markdown-panel', contentClassName)

  return (
    <div className={cn('rounded-md border border-slate-400 dark:border-gray-600', className)}>
      <div className="flex items-center justify-between gap-2 border-b border-slate-300 bg-surface px-1.5 py-1 dark:border-gray-700 dark:bg-gray-900/50">
        <div className="flex flex-wrap items-center gap-0.5">
          {TOOLBAR_ACTIONS.map(item => (
            <button
              key={item.action}
              type="button"
              disabled={disabled || preview}
              title={item.shortcut ? `${item.label} (${item.shortcut})` : item.label}
              aria-label={item.label}
              onMouseDown={event => event.preventDefault()}
              onClick={() => applyAction(item.action)}
              className={cn(
                'rounded p-1 text-gray-500 transition-colors',
                'hover:bg-slate-300 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200',
                'disabled:pointer-events-none disabled:opacity-40',
              )}
            >
              {item.icon}
            </button>
          ))}
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => setPreview(current => !current)}
          className={cn(
            'inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] text-gray-500 transition-colors',
            'hover:bg-slate-300 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200',
            'disabled:pointer-events-none disabled:opacity-40',
          )}
        >
          {preview ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
          {preview ? 'Edit' : 'Preview'}
        </button>
      </div>

      {preview ? (
        <div className={cn('px-3 py-2', panelClass, previewClassName)}>
          {value.trim() ? (
            <DescriptionMarkdown>{value}</DescriptionMarkdown>
          ) : (
            <p className="text-xs text-gray-400 dark:text-gray-500">Nothing to preview</p>
          )}
        </div>
      ) : (
        <textarea
          ref={textareaRef}
          value={value}
          disabled={disabled}
          rows={rows}
          placeholder={placeholder}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          className={cn(
            'block w-full resize-none rounded-b-md border-0 bg-surface-elevated px-3 py-2 text-sm shadow-none',
            'text-gray-900 placeholder-gray-400 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500',
            'focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500',
            panelClass,
            textareaClassName,
          )}
        />
      )}
    </div>
  )
}
