import { Component } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'
import { useRecommendations } from '../hooks/useRecommendations'
import ProductCard from '../components/ProductCard/ProductCard'
import SkeletonCard from '../components/ProductCard/SkeletonCard'
import ExplanationPanel from '../components/ExplanationPanel/ExplanationPanel'
import useAppStore, { DEMO_USERS } from '../store/appStore'
import { recordInteraction } from '../services/api'

class ProductCardErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    console.warn('[ProductCard] render error caught by boundary:', error?.message)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card p-5 flex flex-col items-center justify-center gap-2 min-h-[260px] text-slate-500">
          <AlertCircle size={24} className="text-slate-600" />
          <p className="text-xs text-center">Product unavailable</p>
        </div>
      )
    }
    return this.props.children
  }
}

const PAGE_VARIANTS = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

function HeroSection() {
  return (
    <div className="text-center mb-10">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <span className="badge bg-cyan-400/10 text-cyan-400 border border-cyan-400/20 text-xs mb-4">
          Production-grade XAI System
        </span>
      </motion.div>

      <motion.h1
        className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-100 mb-4 leading-tight"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
      >
        AI That{' '}
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
          Explains Itself
        </span>
      </motion.h1>

      <motion.p
        className="text-slate-400 text-lg max-w-2xl mx-auto leading-relaxed"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.25 }}
      >
        Real-time XGBoost recommendations with SHAP explanations and GPT-4o-mini
        summaries. Every recommendation shows{' '}
        <span className="text-slate-300">exactly why</span> it was made.
      </motion.p>
    </div>
  )
}

function UserSelector({ currentUser, onSelect }) {
  return (
    <motion.div
      className="flex flex-wrap justify-center gap-3 mb-10"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
    >
      {DEMO_USERS.map((user) => (
        <button
          key={user.id}
          onClick={() => onSelect(user)}
          className={clsx(
            'flex items-center gap-2 px-5 py-2.5 rounded-full border text-sm font-medium transition-all duration-200',
            currentUser?.id === user.id
              ? 'bg-cyan-400/15 border-cyan-400/60 text-cyan-400 shadow-glow'
              : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500 hover:text-slate-100'
          )}
        >
          <span>{user.emoji}</span>
          {user.name}
        </button>
      ))}
    </motion.div>
  )
}

function RecommendationGrid({ userId }) {
  const { data, isLoading, isError, error, refetch } = useRecommendations(userId)
  const setOpenExplanationId = useAppStore((s) => s.setOpenExplanationId)

  function handleExplain(recommendationId, productId) {
    setOpenExplanationId(recommendationId)
    if (userId && productId) {
      recordInteraction(userId, productId, 'view').catch(() => {})
    }
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4 text-slate-400">
        <AlertCircle size={36} className="text-red-400" />
        <p className="text-base font-medium text-slate-300">Could not load recommendations</p>
        <p className="text-sm text-slate-500 max-w-md text-center">{error?.message}</p>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600
                     text-slate-300 rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          Try again
        </button>
      </div>
    )
  }

  const recommendations = data?.recommendations || []

  return (
    <>
      {/* New-user trending banner */}
      {data?.is_new_user && (
        <div className="mb-5 flex items-center gap-3 px-4 py-3 rounded-xl
                        bg-violet-400/10 border border-violet-400/20 text-sm text-violet-300">
          <span className="text-lg">✨</span>
          <span>
            <span className="font-semibold">Trending picks</span>
            {' '}— recommendations personalise as you explore products
          </span>
        </div>
      )}

      {/* Header row */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-slate-100 font-semibold text-lg">
            {data?.is_new_user ? 'Trending right now' : 'Recommended for you'}
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            {data?.is_new_user
              ? 'Trending picks · Personalises as you explore'
              : 'Based on your taste profile · Updates in real time'}
          </p>
          {data && (
            <p className="text-slate-500 text-xs mt-0.5">
              {data.cached ? '⚡ Served from cache' : '🤖 Fresh ML inference'} ·{' '}
              {data.response_time_ms}ms
            </p>
          )}
        </div>
        {!isLoading && (
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-slate-400
                       hover:text-slate-200 hover:bg-slate-700/50 rounded-lg text-xs
                       transition-colors border border-slate-700/50"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        )}
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        <AnimatePresence mode="wait">
          {isLoading
            ? Array.from({ length: 5 }).map((_, i) => (
                <motion.div key={`skel-${i}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.05 }}>
                  <SkeletonCard />
                </motion.div>
              ))
            : recommendations.map((rec, i) => (
                <motion.div key={rec.recommendation_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07 }}
                >
                  <ProductCardErrorBoundary>
                    <ProductCard
                      recommendation={rec}
                      onExplain={handleExplain}
                    />
                  </ProductCardErrorBoundary>
                </motion.div>
              ))}
        </AnimatePresence>
      </div>

      {/* Empty state */}
      {!isLoading && recommendations.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <p className="text-4xl mb-3">📦</p>
          <p className="font-medium text-slate-400">No recommendations yet</p>
          <p className="text-sm mt-1">Run the SQL migration and seed script first</p>
        </div>
      )}
    </>
  )
}

export default function Home() {
  const currentUser = useAppStore((s) => s.currentUser)
  const setCurrentUser = useAppStore((s) => s.setCurrentUser)

  return (
    <motion.div
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      variants={PAGE_VARIANTS}
      initial="hidden"
      animate="visible"
    >
      <HeroSection />
      <UserSelector currentUser={currentUser} onSelect={setCurrentUser} />
      <RecommendationGrid userId={currentUser?.id} />
      <ExplanationPanel />
    </motion.div>
  )
}
