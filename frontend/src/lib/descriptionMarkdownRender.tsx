import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'

export const descriptionSanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    a: [...(defaultSchema.attributes?.a ?? []), 'target', 'rel'],
  },
}

export const descriptionRemarkPlugins = [remarkGfm]
export const descriptionRehypePlugins = [rehypeSanitize(descriptionSanitizeSchema)]

export function isExternalMarkdownLink(
  href: string | undefined,
  pageOrigin?: string,
): boolean {
  if (!href) return false

  const trimmed = href.trim()
  if (!trimmed) return false

  if (
    trimmed.startsWith('#') ||
    trimmed.startsWith('/') ||
    trimmed.startsWith('.') ||
    !/^[a-z][a-z0-9+.-]*:/i.test(trimmed)
  ) {
    return false
  }

  const origin =
    pageOrigin ??
    (typeof globalThis.window !== 'undefined' ? globalThis.window.location.origin : undefined)

  if (!origin) return false

  try {
    const url = new URL(trimmed)
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return false
    return url.origin !== origin
  } catch {
    return false
  }
}

export const descriptionMarkdownComponents: Components = {
  a: ({ href, children, ...props }) => {
    const external = isExternalMarkdownLink(href)
    return (
      <a
        href={href}
        {...props}
        target={external ? '_blank' : undefined}
        rel={external ? 'noopener noreferrer' : undefined}
      >
        {children}
      </a>
    )
  },
}
