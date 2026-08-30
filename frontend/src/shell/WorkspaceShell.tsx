import { Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { useEffect, useRef } from "react";
import { TopBar } from "./TopBar";
import { ActivityBar } from "./ActivityBar";
import { Footer } from "./Footer";
import { NotificationsTray } from "./NotificationsTray";
import { pushNotification } from "../store/notifications";
import { useNamespacePermissions } from "../hooks/useNamespacePermissions";
import { PermissionDenied } from "../components/items/PermissionDenied";
import { Skeleton } from "../components/ui/Skeleton";

interface DefaultNamespaceRedirectState {
  defaultNamespaceRedirect?: boolean;
}

export function WorkspaceShell() {
  const { namespace } = useParams<{ namespace: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const handledRedirect = useRef(false);
  const { isLoading, canRead } = useNamespacePermissions(namespace);

  useEffect(() => {
    const state = location.state as DefaultNamespaceRedirectState | null;
    if (!state?.defaultNamespaceRedirect || handledRedirect.current) return;
    handledRedirect.current = true;
    navigate(location.pathname + location.search, {
      replace: true,
      state: null,
    });
    pushNotification(
      "info",
      "Opened your default namespace",
      "Use All namespaces in the user menu to browse every namespace.",
    );
  }, [location.pathname, location.search, location.state, navigate]);

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col bg-surface-canvas dark:bg-gray-950">
        <TopBar />
        <div className="flex flex-1 items-center justify-center pt-12 pb-7">
          <Skeleton className="h-8 w-48" />
        </div>
        <Footer />
        <NotificationsTray />
      </div>
    );
  }

  if (!canRead) {
    return (
      <div className="flex h-screen flex-col bg-surface-canvas dark:bg-gray-950">
        <TopBar />
        <div className="flex flex-1 flex-col pt-12 pb-7">
          <PermissionDenied message="You do not have permission to access this namespace." />
        </div>
        <Footer />
        <NotificationsTray />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-surface-canvas dark:bg-gray-950">
      <TopBar />
      <div className="flex flex-1 overflow-hidden pt-12 pb-7">
        <ActivityBar />
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden pl-12">
          <Outlet />
        </div>
      </div>
      <Footer />
      <NotificationsTray />
    </div>
  );
}
