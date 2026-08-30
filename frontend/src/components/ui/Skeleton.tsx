import { cn } from "./cn";

interface SkeletonProps {
  className?: string;
  lines?: number;
}

export function Skeleton({ className, lines = 1 }: SkeletonProps) {
  return (
    <>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "animate-pulse rounded bg-slate-300 dark:bg-gray-700",
            className ?? "h-4 w-full",
          )}
          style={lines > 1 ? { opacity: 1 - i * 0.15 } : undefined}
        />
      ))}
    </>
  );
}

export function SkeletonList({
  count = 5,
  itemClassName,
}: {
  count?: number;
  itemClassName?: string;
}) {
  return (
    <div className="space-y-2 p-2">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className={itemClassName ?? "h-8 w-full"} />
      ))}
    </div>
  );
}
