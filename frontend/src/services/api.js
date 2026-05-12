import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Something went wrong'
    return Promise.reject(new Error(message))
  }
)

export const getRecommendations = (userId, limit = 5, categoryFilter = null) =>
  api
    .post('/api/v1/recommendations', {
      user_id: userId,
      limit,
      ...(categoryFilter ? { category_filter: categoryFilter } : {}),
    })
    .then((r) => r.data)

export const getExplanation = (recommendationId) =>
  api.get(`/api/v1/explain/${recommendationId}`).then((r) => r.data)

export const getGlobalFeatureImportance = () =>
  api.get('/api/v1/explain/global/feature-importance').then((r) => r.data)

export const getDashboardStats = () =>
  api.get('/api/v1/dashboard/stats').then((r) => r.data)

export const getModelPerformance = () =>
  api.get('/api/v1/dashboard/model-performance').then((r) => r.data)

export const recordInteraction = (userId, productId, actionType, rating = null) =>
  api
    .post('/api/v1/users/interaction', {
      user_id: userId,
      product_id: productId,
      action_type: actionType,
      ...(rating !== null ? { rating } : {}),
    })
    .then((r) => r.data)

/**
 * Fire-and-forget interaction tracker.
 * Never throws — safe to call without await from any component.
 */
export const trackInteraction = (userId, productId, actionType, token = null) => {
  if (!userId || !productId) return
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  api
    .post(
      '/api/v1/users/interaction',
      { user_id: userId, product_id: productId, action_type: actionType },
      { headers },
    )
    .catch((err) => console.warn('[trackInteraction]', actionType, err?.message))
}

export const getHealth = () => api.get('/health').then((r) => r.data)

export const loginUser = (email, password) =>
  api.post('/api/v1/users/login', { email, password }).then((r) => r.data)

export const registerUser = (name, email, password) =>
  api.post('/api/v1/users/register', { name, email, password }).then((r) => r.data)

export const getUserProfile = (userId) =>
  api.get(`/api/v1/users/${userId}/profile/detail`).then((r) => r.data)

export default api
