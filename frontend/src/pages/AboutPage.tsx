import { Info } from 'lucide-react'
import {
  LICENSE_NAME,
  LICENSE_SPDX,
  PRODUCT_NAME,
  PRODUCT_NOTICE,
  PRODUCT_VERSION,
} from '../lib/productInfo'

export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center gap-2">
        <Info className="h-5 w-5 text-brand-600 dark:text-brand-400" />
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">About product</h1>
      </div>

      <dl className="space-y-5 text-sm">
        <div>
          <dt className="font-medium text-gray-500 dark:text-gray-400">Product</dt>
          <dd className="mt-1 font-mono text-gray-900 dark:text-gray-100">{PRODUCT_NAME}</dd>
        </div>
        <div>
          <dt className="font-medium text-gray-500 dark:text-gray-400">Version</dt>
          <dd className="mt-1 font-mono text-gray-900 dark:text-gray-100">{PRODUCT_VERSION}</dd>
        </div>
        <div>
          <dt className="font-medium text-gray-500 dark:text-gray-400">License</dt>
          <dd className="mt-1 text-gray-900 dark:text-gray-100">
            {LICENSE_NAME}
            <span className="ml-2 font-mono text-xs text-gray-500 dark:text-gray-400">
              ({LICENSE_SPDX})
            </span>
          </dd>
        </div>
        <div>
          <dt className="font-medium text-gray-500 dark:text-gray-400">Notice</dt>
          <dd className="mt-2 whitespace-pre-wrap rounded-lg border bg-surface-elevated px-4 py-3 font-mono text-xs leading-relaxed text-gray-800 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
            {PRODUCT_NOTICE}
          </dd>
        </div>
      </dl>
    </div>
  )
}
