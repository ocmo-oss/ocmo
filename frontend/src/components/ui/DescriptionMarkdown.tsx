import ReactMarkdown from "react-markdown";
import {
  descriptionMarkdownComponents,
  descriptionRehypePlugins,
  descriptionRemarkPlugins,
} from "../../lib/descriptionMarkdownRender";
import { cn } from "./cn";

export const descriptionMarkdownClassName =
  "item-markdown text-xs leading-relaxed text-gray-500 dark:text-gray-400";

interface DescriptionMarkdownProps {
  children: string;
  className?: string;
}

export function DescriptionMarkdown({
  children,
  className,
}: DescriptionMarkdownProps) {
  return (
    <div className={cn(descriptionMarkdownClassName, className)}>
      <ReactMarkdown
        remarkPlugins={descriptionRemarkPlugins}
        rehypePlugins={descriptionRehypePlugins}
        components={descriptionMarkdownComponents}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
