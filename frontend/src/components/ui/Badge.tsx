import { cn } from "./cn";
import type { ItemType } from "../../api/types";

type Variant = "default" | "success" | "warning" | "error" | "info";

const variants: Record<Variant, string> = {
  default: "bg-slate-200 text-slate-800 dark:bg-gray-700 dark:text-gray-300",
  success:
    "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  warning:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  error: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  info: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
};

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

const typeVariant: Record<ItemType, Variant> = {
  config: "info",
  template: "success",
  secret: "warning",
  resolver: "default",
  folder: "default",
};

export function TypeBadge({ type }: { type: ItemType }) {
  return <Badge variant={typeVariant[type]}>{type}</Badge>;
}
