import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";
import { Footer } from "./Footer";
import { NotificationsTray } from "./NotificationsTray";

export function GlobalShell() {
  return (
    <div className="flex h-screen flex-col bg-surface-canvas dark:bg-gray-950">
      <TopBar />
      <main className="flex-1 overflow-auto pt-12 pb-7">
        <Outlet />
      </main>
      <Footer />
      <NotificationsTray />
    </div>
  );
}
