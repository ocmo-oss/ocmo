import { createPatch } from 'diff'
import { cn } from '../components/ui/cn'

export function renderUnifiedDiff(
  from: string,
  to: string,
  fileName: string,
  className?: string,
) {
  const patch = from === to ? 'No differences\n' : createPatch(fileName, from, to)
  const lines = patch.split('\n')

  return (
    <pre
      className={cn(
        'h-full min-h-0 w-full overflow-auto rounded bg-gray-950 p-4 text-xs font-mono text-gray-200',
        className,
      )}
    >
      {lines.map((line, i) => {
        let cls = 'text-gray-400'
        if (line.startsWith('+') && !line.startsWith('+++')) cls = 'text-green-400'
        else if (line.startsWith('-') && !line.startsWith('---')) cls = 'text-red-400'
        else if (line.startsWith('@')) cls = 'text-blue-400'
        return (
          <span key={i} className={`${cls} block whitespace-pre-wrap`}>
            {line}
          </span>
        )
      })}
    </pre>
  )
}
