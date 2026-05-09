import { useQuery } from '@tanstack/react-query'
import { getExplanation } from '../services/api'

export function useExplanation(recommendationId) {
  return useQuery({
    queryKey: ['explanation', recommendationId],
    queryFn: () => getExplanation(recommendationId),
    staleTime: 300_000,
    gcTime: 300_000,
    enabled: !!recommendationId,
    retry: 1,
  })
}
