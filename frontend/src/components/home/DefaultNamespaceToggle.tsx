import type { MouseEvent } from 'react'
import { House } from 'lucide-react'
import { useDefaultNamespace } from '../../store/defaultNamespace'
import { Tooltip } from '../ui/Tooltip'
import { cn } from '../ui/cn'
import { showToast } from '../ui/Toast'

export function DefaultNamespaceToggle({
  namespace,
}: {
  namespace: string
}) {
  const { namespace: defaultNamespace, toggleDefaultNamespace } = useDefaultNamespace()
  const isDefault = defaultNamespace === namespace

  const handleClick = (e: MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const wasDefault = isDefault
    toggleDefaultNamespace(namespace)
    if (wasDefault) {
      showToast('Default namespace cleared')
    } else {
      showToast(`"${namespace}" is now your default namespace`)
    }
  }

  return (
    <Tooltip
      side="right"
      align="center"
      content={
        isDefault
          ? 'Default namespace (click to clear)'
          : 'Set as default namespace'
      }
    >
      <button
        type="button"
        onClick={handleClick}
        aria-label={
          isDefault
            ? `Clear default namespace (${namespace})`
            : `Set ${namespace} as default namespace`
        }
        aria-pressed={isDefault}
        className={cn(
          'rounded p-1.5 transition-colors',
          isDefault
            ? 'text-brand-600 hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-brand-900/30'
            : 'text-gray-300 hover:bg-slate-200 hover:text-gray-500 dark:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-400',
        )}
      >
        <House className={cn('h-4 w-4', isDefault && 'fill-current')} />
      </button>
    </Tooltip>
  )
}
