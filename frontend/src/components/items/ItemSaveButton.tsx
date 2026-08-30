import type { Ref, KeyboardEvent } from "react";
import { Save } from "lucide-react";
import { Button } from "../ui/Button";
import { Tooltip } from "../ui/Tooltip";

export function ItemSaveButton({
  label,
  loading,
  disabled,
  onClick,
  buttonRef,
  showEnterHint,
  enterHint,
  onKeyDown,
  className,
}: {
  label: string;
  loading?: boolean;
  disabled?: boolean;
  onClick: () => void;
  buttonRef: Ref<HTMLButtonElement>;
  showEnterHint: boolean;
  enterHint: string;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
  className?: string;
}) {
  return (
    <Tooltip
      content={enterHint}
      open={showEnterHint}
      showOnHover={false}
      side="bottom"
      align="end"
    >
      <Button
        ref={buttonRef}
        variant="primary"
        size="sm"
        loading={loading}
        disabled={disabled}
        onClick={onClick}
        onKeyDown={onKeyDown}
        className={className}
      >
        <Save className="h-3.5 w-3.5" />
        {label}
      </Button>
    </Tooltip>
  );
}
