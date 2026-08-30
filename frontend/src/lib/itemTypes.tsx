import {
  FileCode,
  FileText,
  Folder,
  Shield,
  type LucideIcon,
} from "lucide-react";
import type { ItemType } from "../api/types";
import { cn } from "../components/ui/cn";
import { Tooltip } from "../components/ui/Tooltip";

export const ITEM_TYPE_LABELS: Record<ItemType, string> = {
  folder: "Folder",
  config: "Config",
  template: "Template",
  secret: "Secret",
  resolver: "Resolver",
};

const ITEM_TYPE_ICONS: Record<Exclude<ItemType, "secret">, LucideIcon> = {
  folder: Folder,
  config: FileText,
  template: FileCode,
  resolver: Shield,
};

const ITEM_TYPE_ICON_CLASS: Record<ItemType, string> = {
  folder: "text-amber-500",
  config: "text-blue-500",
  template: "text-green-500",
  secret: "text-yellow-600",
  resolver: "text-gray-500",
};

const sizeClass = {
  sm: "h-3.5 w-3.5",
  md: "h-4 w-4",
} as const;

function SecretIcon({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-[0.7rem] min-w-[0.85rem] items-center justify-center rounded-[3px] border border-yellow-600 px-0.5 text-yellow-600",
        className,
      )}
      aria-hidden="true"
    >
      <span className="font-mono text-[10px] font-bold leading-none tracking-[-0.15em]">
        ***
      </span>
    </span>
  );
}

export function ItemIcon({
  type,
  size = "md",
  className,
  showTooltip = true,
}: {
  type: ItemType;
  size?: keyof typeof sizeClass;
  className?: string;
  showTooltip?: boolean;
}) {
  const icon =
    type === "secret" ? (
      <SecretIcon />
    ) : (
      (() => {
        const Icon = ITEM_TYPE_ICONS[type];
        return (
          <Icon
            className={cn(
              sizeClass[size],
              ITEM_TYPE_ICON_CLASS[type],
              className,
            )}
            aria-hidden="true"
          />
        );
      })()
    );

  const labeled = (
    <span
      className={cn(
        sizeClass[size],
        "inline-flex shrink-0 items-center justify-center",
      )}
      aria-label={ITEM_TYPE_LABELS[type]}
    >
      {icon}
    </span>
  );

  if (!showTooltip) return labeled;

  return <Tooltip content={ITEM_TYPE_LABELS[type]}>{labeled}</Tooltip>;
}
