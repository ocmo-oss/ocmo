import React from 'react'
import { NavLink, useLocation, useParams } from 'react-router-dom'
import { FolderOpen, ClipboardList, Settings, Lock, Shield, GitCompare } from 'lucide-react'
import { cn } from '../components/ui/cn'
import { useNamespacePermissions } from '../hooks/useNamespacePermissions'
import { useLockPermissions } from '../hooks/useLockPermissions'
import { permissionsConfigPath } from '../lib/builtinPaths'

function isNamespaceRoute(pathname: string, segment: string): boolean {
  return new RegExp(`^/ns/[^/]+/${segment}(?:/|$)`).test(pathname)
}

interface Area {
  id: string
  label: string
  icon: React.ReactNode
  path: (ns: string) => string
  isActive?: (pathname: string) => boolean
  visible: (gates: AreaVisibility) => boolean
}

interface AreaVisibility {
  canRead: boolean
  canWrite: boolean
  canAudit: boolean
  lockCanRead: boolean
}

const AREAS: Area[] = [
  {
    id: 'configs',
    label: 'Tree',
    icon: <FolderOpen className="h-5 w-5" />,
    path: ns => `/ns/${ns}/configs`,
    isActive: pathname =>
      isNamespaceRoute(pathname, 'configs')
      && !pathname.includes(`/configs/${permissionsConfigPath()}`),
    visible: gates => gates.canRead,
  },
  {
    id: 'permissions',
    label: 'Permissions',
    icon: <Shield className="h-5 w-5" />,
    path: ns => `/ns/${ns}/configs/${permissionsConfigPath()}`,
    isActive: pathname => pathname.includes(`/configs/${permissionsConfigPath()}`),
    visible: gates => gates.canWrite,
  },
  {
    id: 'locks',
    label: 'Locks',
    icon: <Lock className="h-5 w-5" />,
    path: ns => `/ns/${ns}/locks`,
    isActive: pathname => isNamespaceRoute(pathname, 'locks'),
    visible: gates => gates.lockCanRead,
  },
  {
    id: 'diff',
    label: 'Cross-config diff',
    icon: <GitCompare className="h-5 w-5" />,
    path: ns => `/ns/${ns}/diff`,
    isActive: pathname => isNamespaceRoute(pathname, 'diff'),
    visible: gates => gates.canRead,
  },
  {
    id: 'settings',
    label: 'Namespace settings',
    icon: <Settings className="h-5 w-5" />,
    path: ns => `/ns/${ns}/settings`,
    isActive: pathname => isNamespaceRoute(pathname, 'settings'),
    visible: gates => gates.canWrite,
  },
  {
    id: 'audit',
    label: 'Audit',
    icon: <ClipboardList className="h-5 w-5" />,
    path: ns => `/ns/${ns}/audit`,
    isActive: pathname => isNamespaceRoute(pathname, 'audit'),
    visible: gates => gates.canAudit,
  },
]

export function ActivityBar() {
  const { namespace } = useParams<{ namespace: string }>()
  const { pathname } = useLocation()
  const nsPermissions = useNamespacePermissions(namespace)
  const lockPermissions = useLockPermissions(namespace)

  if (!namespace) return null

  const gates: AreaVisibility = {
    canRead: nsPermissions.canRead,
    canWrite: nsPermissions.canWrite,
    canAudit: nsPermissions.canAudit,
    lockCanRead: lockPermissions.canRead,
  }

  const visibleAreas = AREAS.filter(area => {
    if (nsPermissions.isLoading || !lockPermissions.isReady) {
      return area.id === 'configs'
    }
    return area.visible(gates)
  })

  return (
    <nav
      className="fixed left-0 top-12 z-20 flex h-[calc(100vh-3rem-1.75rem)] w-12 flex-col items-center gap-1 border-r bg-surface py-2 dark:border-gray-700 dark:bg-gray-900"
      aria-label="Activity bar"
    >
      {visibleAreas.map(area => {
        const active = area.isActive ? area.isActive(pathname) : undefined

        return (
          <NavLink
            key={area.id}
            to={area.path(namespace)}
            title={area.label}
            end={!area.isActive}
            className={({ isActive }) =>
              cn(
                'flex h-10 w-10 items-center justify-center rounded-md transition-colors',
                'text-gray-500 hover:bg-slate-300 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100',
                (active ?? isActive) && 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
              )
            }
            aria-label={area.label}
          >
            {area.icon}
          </NavLink>
        )
      })}
    </nav>
  )
}
