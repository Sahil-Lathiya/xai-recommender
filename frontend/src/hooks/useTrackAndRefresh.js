import { useQueryClient } from '@tanstack/react-query'
import { trackInteraction } from '../services/api'

/**
 * Returns a function that tracks a user interaction then immediately
 * invalidates the recommendations cache so the next render gets fresh ML results.
 */
export function useTrackAndRefresh(userId, token = null) {
  const queryClient = useQueryClient()

  return function trackAndRefresh(productId, actionType) {
    if (!userId || !productId) return
    trackInteraction(userId, productId, actionType, token)
    queryClient.invalidateQueries({ queryKey: ['recommendations', userId] })
  }
}
