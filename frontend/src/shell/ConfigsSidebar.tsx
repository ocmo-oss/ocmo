import { TreeSearch } from '../components/tree/TreeSearch'
import { TreeNav } from '../components/tree/TreeNav'
import { CreateItemButton } from '../components/tree/CreateItemButton'

export function ConfigsSidebar() {
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r bg-surface dark:border-gray-700 dark:bg-gray-900">
      <div className="flex shrink-0 items-start gap-1 border-b p-2 dark:border-gray-700">
        <div className="min-w-0 flex-1">
          <TreeSearch />
        </div>
        <CreateItemButton />
      </div>
      <div className="flex-1 overflow-auto">
        <TreeNav />
      </div>
    </aside>
  )
}
