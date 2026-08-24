import { useEffect, useRef } from 'react'
import { Activity } from 'lucide-react'
import { formatHealthDetail, useHealthStore } from '../store/health'
import { fetchHealth, fetchVersion } from '../api/client'
import { formatFetchFailureMessage } from '../lib/apiAvailability'
import { env } from '../env'
import { pushNotification } from '../store/notifications'
import { cn } from '../components/ui/cn'

type HealthStatus = 'checking' | 'healthy' | 'unhealthy' | 'unavailable'

export function Footer() {
  const { health, healthError, version, setHealthError, applyVersionResponse, setVersionBootstrapFallback } = useHealthStore()
  const lastStatus = useRef<HealthStatus>('checking')

  useEffect(() => {
    if (useHealthStore.getState().version) return
    fetchVersion()
      .then(applyVersionResponse)
      .catch(() => {
        setVersionBootstrapFallback()
      })
  }, [applyVersionResponse, setVersionBootstrapFallback])

  useEffect(() => {
    const check = async () => {
      if (document.hidden) return
      try {
        await fetchHealth()
        const h = useHealthStore.getState().health
        if (!h) return
        const status: HealthStatus = h.status === 'ok' ? 'healthy' : 'unhealthy'

        if (status === 'unhealthy' && lastStatus.current === 'healthy') {
          pushNotification(
            'warning',
            'API unhealthy',
            formatHealthDetail(h, null),
          )
        }
        if (status === 'healthy' && (lastStatus.current === 'unhealthy' || lastStatus.current === 'unavailable')) {
          pushNotification('info', 'API healthy', 'Health checks are passing again')
        }
        lastStatus.current = status
      } catch (err) {
        const message = formatFetchFailureMessage(err)
        setHealthError(message)
        if (lastStatus.current === 'healthy' || lastStatus.current === 'checking') {
          pushNotification('error', 'API unavailable', message)
        }
        lastStatus.current = 'unavailable'
      }
    }

    void check()
    const id = setInterval(() => void check(), 30_000)
    const onVisibility = () => void check()
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [setHealthError])

  const status: HealthStatus = healthError
    ? 'unavailable'
    : health && health.status !== 'ok'
      ? 'unhealthy'
      : health?.status === 'ok'
        ? 'healthy'
        : 'checking'

  const label = status === 'healthy'
    ? 'API healthy'
    : status === 'unhealthy'
      ? 'API unhealthy'
      : status === 'unavailable'
        ? 'API unavailable'
        : 'API checking…'

  const detail = formatHealthDetail(health, healthError)
  const swaggerUrl = `${env.apiBase}/api/docs`

  return (
    <footer className="fixed inset-x-0 bottom-0 z-20 flex h-7 items-center justify-between border-t bg-surface px-3 text-[11px] text-gray-500 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-400">
      <a
        href={swaggerUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="truncate hover:text-brand-600 hover:underline dark:hover:text-brand-400"
        title="Open API documentation (Swagger)"
      >
        OCMO{version ? ` v${version}` : ''}
      </a>

      <div
        className="group relative flex items-center gap-1"
        title={detail}
      >
        <Activity className={cn(
          'h-3 w-3 shrink-0',
          status === 'healthy' && 'text-green-500',
          status === 'unhealthy' && 'text-red-500',
          status === 'unavailable' && 'text-red-500',
          status === 'checking' && 'text-gray-400',
        )} />
        <span className={cn(
          status === 'healthy' && 'text-green-600 dark:text-green-400',
          status === 'unhealthy' && 'text-red-600 dark:text-red-400',
          status === 'unavailable' && 'text-red-600 dark:text-red-400',
          status === 'checking' && 'text-gray-500 dark:text-gray-400',
        )}>
          {label}
        </span>

        {(status === 'unhealthy' || status === 'unavailable') && (
          <div className="pointer-events-none absolute bottom-full right-0 z-50 mb-1 hidden w-max max-w-xs rounded border bg-surface-elevated px-2 py-1.5 text-[10px] leading-snug text-gray-600 shadow-md group-hover:block dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 whitespace-pre-wrap">
            {detail}
          </div>
        )}
      </div>
    </footer>
  )
}
