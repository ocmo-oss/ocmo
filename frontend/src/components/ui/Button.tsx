import React from "react";
import { cn } from "./cn";

type Variant =
  | "primary"
  | "secondary"
  | "success"
  | "danger"
  | "ghost"
  | "outline-primary"
  | "outline-success"
  | "outline-warning"
  | "outline-danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 focus-visible:ring-brand-500 dark:bg-brand-500 dark:hover:bg-brand-600",
  secondary:
    "bg-surface-elevated text-slate-800 border border-slate-400 hover:bg-surface dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700",
  success:
    "bg-green-600 text-white hover:bg-green-700 focus-visible:ring-green-500 dark:bg-green-600 dark:hover:bg-green-500",
  danger: "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500",
  ghost:
    "text-slate-700 hover:bg-slate-200/70 dark:text-gray-300 dark:hover:bg-gray-800",
  "outline-primary":
    "border border-brand-600 text-brand-700 bg-transparent hover:bg-brand-50 dark:border-brand-500 dark:text-brand-300 dark:hover:bg-brand-950/40",
  "outline-success":
    "border border-green-600 text-green-700 bg-transparent hover:bg-green-50 dark:border-green-500 dark:text-green-400 dark:hover:bg-green-950/30",
  "outline-warning":
    "border border-yellow-600 text-yellow-800 bg-transparent hover:bg-yellow-50 dark:border-yellow-500 dark:text-yellow-300 dark:hover:bg-yellow-950/30",
  "outline-danger":
    "border border-red-600 text-red-700 bg-transparent hover:bg-red-50 dark:border-red-500 dark:text-red-400 dark:hover:bg-red-950/30",
};

const sizes: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-3.5 py-1.5 text-sm",
  lg: "px-5 py-2.5 text-base",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "secondary",
      size = "md",
      loading,
      disabled,
      children,
      className,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        {...props}
        disabled={disabled ?? loading}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-md font-medium transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
          "disabled:pointer-events-none disabled:opacity-50",
          variants[variant],
          sizes[size],
          className,
        )}
      >
        {loading && (
          <svg
            className="h-3.5 w-3.5 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  },
);
