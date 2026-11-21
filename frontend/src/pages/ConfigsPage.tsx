import { Outlet, useLocation, useParams } from "react-router-dom";
import { ConfigsSidebar } from "../shell/ConfigsSidebar";
import { isChangeRequestDetailRoute } from "../lib/changeRequestRoutes";

export function ConfigsPage() {
  const { namespace } = useParams<{ namespace: string }>();
  const { pathname } = useLocation();
  const hideTreeSidebar = isChangeRequestDetailRoute(pathname);

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden">
      {!hideTreeSidebar && <ConfigsSidebar />}
      <main
        className="flex flex-1 min-h-0 flex-col overflow-hidden"
        role="main"
      >
        <Outlet context={{ namespace }} />
      </main>
    </div>
  );
}
