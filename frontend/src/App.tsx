import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { useAuth } from "./auth/useAuth";
import { LoginPage, LoginCallbackPage } from "./pages/LoginPage";
import { SilentCallbackPage } from "./pages/SilentCallbackPage";
import { HomePage } from "./pages/HomePage";
import { DefaultNamespaceGate } from "./pages/DefaultNamespaceGate";
import { ConfigsPage } from "./pages/ConfigsPage";
import { CreateItemPage } from "./pages/CreateItemPage";
import { ItemDetailPage } from "./pages/ItemDetailPage";
import { NamespaceAuditPage, GlobalAuditPage } from "./pages/AuditPage";
import { GlobalPermissionsPage } from "./pages/GlobalPermissionsPage";
import { AboutPage } from "./pages/AboutPage";
import { LocksPage } from "./pages/LocksPage";
import { CrossConfigDiffPage } from "./pages/CrossConfigDiffPage";
import { NamespaceSettingsPage } from "./pages/NamespaceSettingsPage";
import { WorkspaceShell } from "./shell/WorkspaceShell";
import { GlobalShell } from "./shell/GlobalShell";
import { RequireGlobalAdmin } from "./auth/RequireGlobalAdmin";
import { LOGIN_PATH } from "./auth/authPaths";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const isAuthenticated = !!user?.access_token && !user.expired;

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to={LOGIN_PATH} replace />;
  }

  return <>{children}</>;
}

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/login/callback",
    element: <LoginCallbackPage />,
  },
  {
    path: "/auth/silent-callback",
    element: <SilentCallbackPage />,
  },
  {
    element: (
      <RequireAuth>
        <GlobalShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DefaultNamespaceGate /> },
      { path: "namespaces", element: <HomePage /> },
      {
        path: "audit",
        element: (
          <RequireGlobalAdmin>
            <GlobalAuditPage />
          </RequireGlobalAdmin>
        ),
      },
      {
        path: "audit/:eventId",
        element: (
          <RequireGlobalAdmin>
            <GlobalAuditPage />
          </RequireGlobalAdmin>
        ),
      },
      {
        path: "permissions/global",
        element: (
          <RequireGlobalAdmin>
            <GlobalPermissionsPage />
          </RequireGlobalAdmin>
        ),
      },
      { path: "about", element: <AboutPage /> },
    ],
  },
  {
    path: "ns/:namespace",
    element: (
      <RequireAuth>
        <WorkspaceShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="configs" replace /> },
      {
        path: "configs",
        element: <ConfigsPage />,
        children: [
          { index: true, element: <ItemDetailPage /> },
          { path: "new/:type", element: <CreateItemPage /> },
          { path: "*", element: <ItemDetailPage /> },
        ],
      },
      { path: "audit", element: <NamespaceAuditPage /> },
      { path: "audit/:eventId", element: <NamespaceAuditPage /> },
      { path: "locks", element: <LocksPage /> },
      { path: "locks/*", element: <LocksPage /> },
      { path: "diff", element: <CrossConfigDiffPage /> },
      { path: "settings", element: <NamespaceSettingsPage /> },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
