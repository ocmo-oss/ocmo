import ReactMarkdown from "react-markdown";
import {
  descriptionMarkdownComponents,
  descriptionRehypePlugins,
  descriptionRemarkPlugins,
  isExternalMarkdownLink,
} from "../../lib/descriptionMarkdownRender";
import {
  isCrLineRefHref,
  linkifyCrLineRefsInMarkdown,
} from "../../lib/changeRequestLineRefs";
import { descriptionMarkdownClassName } from "../ui/DescriptionMarkdown";
import { cn } from "../ui/cn";
import type { Components } from "react-markdown";

export function ChangeRequestLineRefMarkdown({
  children,
  className,
  onLineRefClick,
}: {
  children: string;
  className?: string;
  onLineRefClick: (hash: string) => void;
}) {
  const source = linkifyCrLineRefsInMarkdown(children);

  const components: Components = {
    ...descriptionMarkdownComponents,
    a: ({ href, children: linkChildren, ...props }) => {
      if (isCrLineRefHref(href)) {
        return (
          <a
            href={href}
            className="cr-line-ref-link font-medium text-brand-700 underline decoration-brand-400 underline-offset-2 hover:text-brand-800 dark:text-brand-300 dark:decoration-brand-600"
            onClick={(event) => {
              event.preventDefault();
              onLineRefClick(href!.slice(1));
            }}
            {...props}
          >
            {linkChildren}
          </a>
        );
      }
      const external = isExternalMarkdownLink(href);
      return (
        <a
          href={href}
          {...props}
          target={external ? "_blank" : undefined}
          rel={external ? "noopener noreferrer" : undefined}
        >
          {linkChildren}
        </a>
      );
    },
  };

  return (
    <div className={cn(descriptionMarkdownClassName, className)}>
      <ReactMarkdown
        remarkPlugins={descriptionRemarkPlugins}
        rehypePlugins={descriptionRehypePlugins}
        components={components}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
