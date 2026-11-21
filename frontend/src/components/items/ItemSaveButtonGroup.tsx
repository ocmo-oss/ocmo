import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type Ref,
} from "react";
import { ChevronDown, Save } from "lucide-react";
import { Button } from "../ui/Button";
import { Tooltip } from "../ui/Tooltip";
import { cn } from "../ui/cn";
import { ItemSaveButton } from "./ItemSaveButton";

export interface ItemSaveExtraAction {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export function ItemSaveButtonGroup({
  label,
  loading,
  disabled,
  onClick,
  buttonRef,
  showEnterHint,
  enterHint,
  onKeyDown,
  className,
  extraActions,
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
  extraActions?: ItemSaveExtraAction[];
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (disabled) setMenuOpen(false);
  }, [disabled]);

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    toggleRef.current?.focus({ preventScroll: true });
  }, []);

  const focusMenuItem = useCallback(
    (index: number) => {
      if (!extraActions?.length) return;
      const len = extraActions.length;
      let i = index;
      for (let n = 0; n < len; n++) {
        const action = extraActions[i];
        if (!action.disabled && !action.loading) {
          itemRefs.current[i]?.focus({ preventScroll: true });
          return;
        }
        i = (i + 1 + len) % len;
      }
    },
    [extraActions],
  );

  const openMenu = useCallback(() => {
    setMenuOpen(true);
    requestAnimationFrame(() => focusMenuItem(0));
  }, [focusMenuItem]);

  const handleToggleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!menuOpen) openMenu();
      else focusMenuItem(0);
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (menuOpen) closeMenu();
      else openMenu();
    }
  };

  const handleMenuItemKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number,
  ) => {
    if (!extraActions?.length) return;
    const len = extraActions.length;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusMenuItem(index + 1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      focusMenuItem(index - 1 + len);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu();
      return;
    }
    if (event.key === "Tab") {
      closeMenu();
    }
  };

  if (!extraActions?.length) {
    return (
      <ItemSaveButton
        label={label}
        loading={loading}
        disabled={disabled}
        onClick={onClick}
        buttonRef={buttonRef}
        showEnterHint={showEnterHint}
        enterHint={enterHint}
        onKeyDown={onKeyDown}
        className={className}
      />
    );
  }

  return (
    <div className={cn("relative inline-flex", className)}>
      <div className="inline-flex">
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
            className="rounded-r-none"
          >
            <Save className="h-3.5 w-3.5" />
            {label}
          </Button>
        </Tooltip>
        <Button
          ref={toggleRef}
          type="button"
          variant="primary"
          size="sm"
          disabled={disabled || loading}
          onClick={() => (menuOpen ? closeMenu() : openMenu())}
          onKeyDown={handleToggleKeyDown}
          className="rounded-l-none border-l border-brand-700/60 px-2 dark:border-brand-800/80"
          aria-label="More save actions"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </Button>
      </div>
      {menuOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={closeMenu} />
          <div
            className="absolute right-0 top-full z-20 mt-1 w-56 rounded-md border bg-surface-elevated py-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
            role="menu"
          >
            {extraActions.map((action, index) => (
              <button
                key={action.label}
                ref={(el) => {
                  itemRefs.current[index] = el;
                }}
                type="button"
                role="menuitem"
                tabIndex={-1}
                className="flex w-full px-3 py-2 text-left text-xs hover:bg-slate-100 focus:bg-slate-100 focus:outline-none disabled:opacity-50 dark:hover:bg-gray-800 dark:focus:bg-gray-800"
                disabled={action.disabled || action.loading}
                onClick={() => {
                  action.onClick();
                  closeMenu();
                }}
                onKeyDown={(e) => handleMenuItemKeyDown(e, index)}
              >
                {action.loading ? "Working…" : action.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
