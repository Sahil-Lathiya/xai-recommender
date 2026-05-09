import { useQuery } from '@tanstack/react-query'
import { getRecommendations } from '../services/api'

export function useRecommendations(userId, limit = 5, categoryFilter = null) {
  return useQuery({
    queryKey: ['recommendations', userId, limit, categoryFilter],
    queryFn: () => getRecommendations(userId, limit, categoryFilter),
    staleTime: 60_000,
    enabled: !!userId,
    retry: 1,
  })
}
