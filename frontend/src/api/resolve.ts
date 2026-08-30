import { api } from "./client";
import type { CastFormatsList, ResolveParametersResponse } from "./types";

export const resolveApi = {
  castFormats: (signal?: AbortSignal) =>
    api.get<CastFormatsList>("/~cast-formats/", { signal }),

  parameters: (
    ns: string,
    path: string,
    params?: Record<string, string | boolean | undefined>,
    signal?: AbortSignal,
  ) =>
    api.get<ResolveParametersResponse>(
      `/ns/${ns}/~resolve-parameters/${path}`,
      { params, signal },
    ),
};
