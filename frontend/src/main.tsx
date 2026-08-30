import "./store/theme"; // apply saved theme before first paint
import "./lib/monacoEnvironment"; // MonacoEnvironment.getWorker before monaco loads
import "./lib/monaco"; // configures Monaco before any editor renders
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import "./index.css";
import { ApiError } from "./api/client";
import { isApiUnavailableStatus } from "./lib/apiAvailability";
import { pushNotification } from "./store/notifications";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on auth/permission errors
        if (
          error instanceof ApiError &&
          [401, 403, 404, 422, 423].includes(error.status)
        ) {
          return false;
        }
        if (error instanceof ApiError && isApiUnavailableStatus(error.status)) {
          return false;
        }
        return failureCount < 2;
      },
      staleTime: 30_000,
    },
    mutations: {
      onError: (error) => {
        if (error instanceof ApiError && error.status === 401) {
          pushNotification("error", "Session expired — please sign in again");
        }
      },
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
