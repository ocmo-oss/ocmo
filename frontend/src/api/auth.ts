import { api } from "./client";
import type { WhoAmI, CanIRequest, CanIResponse } from "./types";

export const authApi = {
  whoami: (signal?: AbortSignal) =>
    api.get<WhoAmI>("/auth/whoami/", { signal }),

  canI: (payload: CanIRequest, signal?: AbortSignal) =>
    api.post<CanIResponse>("/auth/can-i/", payload, { signal }),
};
