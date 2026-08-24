import { create } from 'zustand'

interface TreeSearchState {
  query: string
  debouncedQuery: string
  setQuery: (query: string) => void
  setDebouncedQuery: (query: string) => void
  clear: () => void
}

export const useTreeSearchStore = create<TreeSearchState>(set => ({
  query: '',
  debouncedQuery: '',
  setQuery: query => set({ query }),
  setDebouncedQuery: debouncedQuery => set({ debouncedQuery }),
  clear: () => set({ query: '', debouncedQuery: '' }),
}))
