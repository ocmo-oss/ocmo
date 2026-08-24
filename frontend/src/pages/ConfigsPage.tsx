import { Outlet, useParams } from 'react-router-dom'
import { ConfigsSidebar } from '../shell/ConfigsSidebar'

export function ConfigsPage() {
  const { namespace } = useParams<{ namespace: string }>()

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden">
      <ConfigsSidebar />
      <main className="flex flex-1 min-h-0 flex-col overflow-hidden" role="main">
        <Outlet context={{ namespace }} />
      </main>
    </div>
  )
}
