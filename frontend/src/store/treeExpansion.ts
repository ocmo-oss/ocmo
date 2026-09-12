import { create } from "zustand";

interface TreeExpansionState {
  isolatedPath: string | null;
  isolateRevision: number;
  isolateToCurrentPath: (path: string) => void;
}

export const useTreeExpansionStore = create<TreeExpansionState>((set) => ({
  isolatedPath: null,
  isolateRevision: 0,
  isolateToCurrentPath: (path) =>
    set((state) => ({
      isolatedPath: path,
      isolateRevision: state.isolateRevision + 1,
    })),
}));
