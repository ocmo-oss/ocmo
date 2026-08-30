import { create } from "zustand";

const STORAGE_KEY = "ocmo-default-namespace";

export function readDefaultNamespace(): string | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    return stored;
  } catch {
    return null;
  }
}

export function writeDefaultNamespace(namespace: string | null): void {
  try {
    if (namespace) {
      localStorage.setItem(STORAGE_KEY, namespace);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // localStorage unavailable
  }
}

interface DefaultNamespaceState {
  namespace: string | null;
  setDefaultNamespace: (namespace: string) => void;
  clearDefaultNamespace: () => void;
  toggleDefaultNamespace: (namespace: string) => void;
}

export const useDefaultNamespace = create<DefaultNamespaceState>(
  (set, get) => ({
    namespace: readDefaultNamespace(),

    setDefaultNamespace: (namespace) => {
      writeDefaultNamespace(namespace);
      set({ namespace });
    },

    clearDefaultNamespace: () => {
      writeDefaultNamespace(null);
      set({ namespace: null });
    },

    toggleDefaultNamespace: (namespace) => {
      const current = get().namespace;
      if (current === namespace) {
        get().clearDefaultNamespace();
      } else {
        get().setDefaultNamespace(namespace);
      }
    },
  }),
);
