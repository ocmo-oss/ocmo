import { Link, useParams } from "react-router-dom";
import {
  Bell,
  CheckCircle,
  ChevronDown,
  House,
  Info,
  LayoutGrid,
  LogOut,
  Moon,
  Sun,
  User,
  ShieldCheck,
  X,
} from "lucide-react";
import { Switch } from "@headlessui/react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/useAuth";
import { useNotifications } from "../store/notifications";
import { useTheme } from "../store/theme";
import { useDefaultNamespace } from "../store/defaultNamespace";
import { NamespaceSelector } from "../components/shell/NamespaceSelector";
import { Tooltip } from "../components/ui/Tooltip";
import { cn } from "../components/ui/cn";
import ocmoLogo from "../assets/logo-large.png";

function OcmoLogo() {
  return (
    <Link to="/" className="flex items-center gap-2 shrink-0">
      <span className="flex h-7 w-7 items-center justify-center rounded bg-surface-elevated p-0.5">
        <img
          src={ocmoLogo}
          alt="OCMO"
          className="h-full w-full object-contain"
        />
      </span>
      <span className="hidden font-semibold text-gray-900 dark:text-gray-100 sm:block text-sm">
        OCMO
      </span>
    </Link>
  );
}

const SUCCESS_PULSE_MS = 2000;

function NotificationsBell() {
  const { notifications, toggleTray, shakeGeneration, successPulseGeneration } =
    useNotifications();
  const count = notifications.length;
  const hasError = notifications.some((n) => n.severity === "error");
  const [shaking, setShaking] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const prevShakeGeneration = useRef(shakeGeneration);
  const prevSuccessGeneration = useRef(successPulseGeneration);
  const successTimerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (shakeGeneration === prevShakeGeneration.current) return;
    prevShakeGeneration.current = shakeGeneration;
    setShaking(true);
    const t = setTimeout(() => setShaking(false), 600);
    return () => clearTimeout(t);
  }, [shakeGeneration]);

  useEffect(() => {
    if (successPulseGeneration === prevSuccessGeneration.current) return;
    prevSuccessGeneration.current = successPulseGeneration;
    setShowSuccess(true);
    clearTimeout(successTimerRef.current);
    successTimerRef.current = setTimeout(
      () => setShowSuccess(false),
      SUCCESS_PULSE_MS,
    );
    return () => clearTimeout(successTimerRef.current);
  }, [successPulseGeneration]);

  return (
    <button
      onClick={toggleTray}
      className={cn(
        "relative rounded p-1.5 transition-all duration-300",
        showSuccess
          ? "bg-green-50 text-green-600 ring-2 ring-green-400/60 dark:bg-green-950/50 dark:text-green-400 dark:ring-green-500/50"
          : "text-gray-500 hover:bg-slate-200 dark:text-gray-400 dark:hover:bg-gray-800",
        !showSuccess && hasError && "text-red-500 dark:text-red-400",
        shaking && !showSuccess && "animate-bell-shake",
      )}
      aria-label={`Notifications${count > 0 ? ` (${count})` : ""}`}
    >
      {showSuccess ? (
        <CheckCircle className="h-4 w-4" />
      ) : (
        <Bell className="h-4 w-4" />
      )}
      {count > 0 && !showSuccess && (
        <span
          className={cn(
            "absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold text-white",
            hasError ? "bg-red-500" : "bg-brand-600",
          )}
        >
          {count > 99 ? "99+" : count}
        </span>
      )}
    </button>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2">
      <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
        {isDark ? (
          <Moon className="h-3.5 w-3.5" />
        ) : (
          <Sun className="h-3.5 w-3.5" />
        )}
        Dark theme
      </div>
      <Switch
        checked={isDark}
        onChange={(checked) => setTheme(checked ? "dark" : "light")}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900",
          isDark ? "bg-brand-600" : "bg-slate-300 dark:bg-gray-700",
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition",
            isDark ? "translate-x-4" : "translate-x-0",
          )}
        />
      </Switch>
    </div>
  );
}

function UserMenu() {
  const { user, whoami, logout, isGlobalAdmin } = useAuth();
  const { namespace: defaultNamespace, clearDefaultNamespace } =
    useDefaultNamespace();
  const [open, setOpen] = useState(false);

  const displayName =
    whoami?.display_name ??
    user?.profile?.name ??
    user?.profile?.preferred_username ??
    "User";
  const subtitle =
    whoami?.auth_type === "user"
      ? (whoami.user_details.email ?? whoami.identifier)
      : whoami?.auth_type === "resolver"
        ? `Resolver · scope: ${whoami.access_scope || "/"}`
        : null;

  const Icon = isGlobalAdmin ? ShieldCheck : User;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex items-center gap-1.5 rounded-md px-2 py-1 text-sm hover:bg-slate-200 dark:hover:bg-gray-800",
          isGlobalAdmin
            ? "text-brand-700 dark:text-brand-400"
            : "text-gray-600 dark:text-gray-300",
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        <span className="hidden max-w-36 truncate sm:block">{displayName}</span>
        <ChevronDown className="h-3 w-3 opacity-60 shrink-0" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-40 w-56 rounded-lg border bg-surface-elevated shadow-lg dark:border-gray-700 dark:bg-gray-900">
            <div className="border-b px-3 py-2.5 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <Icon
                  className={cn(
                    "h-5 w-5 shrink-0",
                    isGlobalAdmin
                      ? "text-brand-600 dark:text-brand-400"
                      : "text-gray-400",
                  )}
                />
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {displayName}
                  </p>
                  {subtitle && (
                    <p className="truncate text-xs text-gray-400">{subtitle}</p>
                  )}
                </div>
              </div>
              {isGlobalAdmin && (
                <span className="mt-1.5 inline-flex items-center gap-1 rounded bg-brand-50 px-1.5 py-0.5 text-[11px] font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                  <ShieldCheck className="h-3 w-3" />
                  Global administrator
                </span>
              )}
            </div>
            <div className="border-b dark:border-gray-700">
              <ThemeToggle />
            </div>
            <Link
              to="/namespaces"
              onClick={() => setOpen(false)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-slate-100 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
              All namespaces
            </Link>
            <Link
              to="/about"
              onClick={() => setOpen(false)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-slate-100 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              <Info className="h-3.5 w-3.5" />
              About product
            </Link>
            {defaultNamespace && (
              <div className="border-b px-3 py-2 dark:border-gray-700">
                <div className="flex items-center gap-2">
                  <Tooltip
                    content="Default namespace"
                    side="left"
                    align="center"
                  >
                    <span
                      className="inline-flex shrink-0 text-brand-600 dark:text-brand-400"
                      aria-hidden="true"
                    >
                      <House className="h-3.5 w-3.5 fill-current" />
                    </span>
                  </Tooltip>
                  <Tooltip
                    content={defaultNamespace}
                    side="left"
                    align="start"
                    className="min-w-0 flex-1 overflow-hidden"
                  >
                    <span className="block truncate font-mono text-xs text-gray-700 dark:text-gray-200">
                      {defaultNamespace}
                    </span>
                  </Tooltip>
                  <Tooltip
                    content="Clear default namespace"
                    side="left"
                    align="center"
                  >
                    <button
                      type="button"
                      onClick={() => {
                        clearDefaultNamespace();
                        setOpen(false);
                      }}
                      aria-label="Clear default namespace"
                      className="shrink-0 rounded p-1 text-gray-400 hover:bg-slate-200 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-200"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </Tooltip>
                </div>
              </div>
            )}
            <button
              onClick={() => {
                void logout();
                setOpen(false);
              }}
              className="flex w-full items-center gap-2 rounded-b-lg px-3 py-2 text-sm text-gray-700 hover:bg-slate-100 dark:text-gray-200 dark:hover:bg-gray-800"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function TopBar() {
  const { namespace } = useParams<{ namespace?: string }>();

  return (
    <header className="fixed inset-x-0 top-0 z-30 flex h-12 items-center gap-3 border-b bg-surface px-3 dark:border-gray-700 dark:bg-gray-950">
      <OcmoLogo />

      {namespace && (
        <>
          <div className="text-gray-300 dark:text-gray-600 select-none">/</div>
          <NamespaceSelector />
        </>
      )}

      <div className="flex-1" />

      <NotificationsBell />
      <UserMenu />
    </header>
  );
}
