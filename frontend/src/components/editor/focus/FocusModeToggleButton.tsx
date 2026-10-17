import { Maximize2 } from "lucide-react";
import { Button } from "../../ui/Button";
import { Tooltip } from "../../ui/Tooltip";
import { cn } from "../../ui/cn";

export function FocusModeToggleButton({
  onClick,
  disabled,
  className,
}: {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <Tooltip content="Focus mode" side="bottom" align="end">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={disabled}
        onClick={onClick}
        aria-label="Enter focus mode"
        title="Focus mode"
        className={cn("mr-1 px-2", className)}
      >
        <Maximize2 className="h-4 w-4" />
      </Button>
    </Tooltip>
  );
}
