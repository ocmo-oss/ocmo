import { useQuery } from '@tanstack/react-query'
import { authApi } from '../api/auth'

export function useCanCreateNamespace(enabled = true) {
  const { data, isLoading } = useQuery({
    queryKey: ['can-i', 'namespace-create'],
    queryFn: ({ signal }) => authApi.canI({ operations: ['namespace:create'] }, signal),
    enabled,
    staleTime: 30_000,
  })

  return {
    isLoading,
    canCreate: data?.allowed['namespace:create'] ?? false,
  }
}
