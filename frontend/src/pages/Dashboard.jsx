import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Activity, Users, BarChart3, DollarSign,
  Loader2, AlertCircle, ArrowLeft, Lock, LogOut,
} from 'lucide-react'
import {
  getDashboardStats,
  getModelPerformance,
  getGlobalFeatureImportance,
} from '../services/api'
import KPICard from '../components/Dashboard/KPICard'
import ModelPerformanceTable from '../components/Dashboard/ModelPerformanceTable'
import FeatureImportanceChart from '../components/Charts/FeatureImportanceChart'
import RecommendationsOverTime from '../components/Charts/RecommendationsOverTime'
import CategoryPie from '../components/Charts/CategoryPie'
import useAppStore from '../store/appStore'

const ADMIN_EMAIL    = 'admin@xairecommender.me'
const ADMIN_PASSWORD = 'XaiAdmin2026!'

const PAGE_VARIANTS = {
  hidden:  { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

function SectionCard({ title, children, className = '' }) {
  return (
    <div className={`card p-5 ${className}`}>
      <h3 className="text-slate-300 text-sm font-semibold uppercase tracking-wide mb-4">
        {title}
      </h3>
      {children}
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-3 text-slate-400">
      <Loader2 size={32} className="animate-spin text-cyan-400" />
      <p className="text-sm">Loading dashboard…</p>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-32 gap-3 text-slate-400">
      <AlertCircle size={32} className="text-red-400" />
      <p className="text-sm text-slate-300">Dashboard unavailable</p>
      <p className="text-xs text-slate-500">{message}</p>
    </div>
  )
}

function AdminLoginForm({ onAuthenticated }) {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setTimeout(() => {
      if (email === ADMIN_EMAIL && password === ADMIN_PASSWORD) {
        onAuthenticated()
      } else {
        setError('Invalid admin credentials')
      }
      setLoading(false)
    }, 350)
  }

  return (
    <motion.div
      className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="w-full max-w-sm">
        <div className="w-14 h-14 rounded-2xl bg-amber-400/10 border border-amber-400/20
                        flex items-center justify-center mx-auto mb-6">
          <Lock size={26} className="text-amber-400" />
        </div>

        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 text-center mb-1">
          Admin Panel
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm text-center mb-8">
          System metrics · admin access only
        </p>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="block text-slate-600 dark:text-slate-400 text-xs font-medium mb-1.5">
              Admin email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@xairecommender.me"
              required
              autoComplete="username"
              className="w-full px-3 py-2.5 rounded-lg text-sm
                         bg-slate-50 dark:bg-slate-800/60
                         border border-slate-200 dark:border-slate-700
                         text-slate-900 dark:text-slate-100
                         placeholder-slate-400 dark:placeholder-slate-600
                         focus:outline-none focus:ring-2 focus:ring-amber-400/40
                         transition-colors"
            />
          </div>

          <div>
            <label className="block text-slate-600 dark:text-slate-400 text-xs font-medium mb-1.5">
              Admin password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              autoComplete="current-password"
              className="w-full px-3 py-2.5 rounded-lg text-sm
                         bg-slate-50 dark:bg-slate-800/60
                         border border-slate-200 dark:border-slate-700
                         text-slate-900 dark:text-slate-100
                         placeholder-slate-400 dark:placeholder-slate-600
                         focus:outline-none focus:ring-2 focus:ring-amber-400/40
                         transition-colors"
            />
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg
                         bg-red-400/10 border border-red-400/20"
            >
              <AlertCircle size={14} className="text-red-400 flex-shrink-0" />
              <p className="text-red-400 text-xs">{error}</p>
            </motion.div>
          )}

          <motion.button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg text-sm font-semibold
                       bg-amber-400 hover:bg-amber-300 text-slate-900
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors duration-200"
            whileTap={{ scale: 0.98 }}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Verifying…
              </span>
            ) : 'Admin Login'}
          </motion.button>
        </form>

        <div className="mt-5 text-center">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-slate-400
                       hover:text-slate-600 dark:hover:text-slate-300 text-sm transition-colors"
          >
            <ArrowLeft size={14} />
            Back to Recommendations
          </Link>
        </div>
      </div>
    </motion.div>
  )
}

export default function Dashboard() {
  const isAdminAuthenticated = useAppStore((s) => s.isAdminAuthenticated)
  const setAdminAuthenticated = useAppStore((s) => s.setAdminAuthenticated)

  // Always call hooks at the top — React rules of hooks.
  // enabled: false prevents fetching until authenticated.
  const stats = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
    enabled: isAdminAuthenticated,
  })

  const performance = useQuery({
    queryKey: ['model-performance'],
    queryFn: getModelPerformance,
    staleTime: 60_000,
    enabled: isAdminAuthenticated,
  })

  const importance = useQuery({
    queryKey: ['global-feature-importance'],
    queryFn: getGlobalFeatureImportance,
    staleTime: 3_600_000,
    enabled: isAdminAuthenticated,
  })

  if (!isAdminAuthenticated) {
    return <AdminLoginForm onAuthenticated={() => setAdminAuthenticated(true)} />
  }

  if (stats.isLoading) return <LoadingState />
  if (stats.isError)   return <ErrorState message={stats.error?.message} />

  const s   = stats.data      || {}
  const perf = performance.data || {}
  const imp  = importance.data  || {}

  return (
    <motion.div
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10"
      variants={PAGE_VARIANTS}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-slate-100">Live Dashboard</h1>
            <span className="badge bg-amber-400/10 text-amber-400 border border-amber-400/20 text-xs">
              Admin View — System Metrics
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Real-time system metrics · auto-refreshes every 30s
          </p>
        </div>
        <button
          onClick={() => setAdminAuthenticated(false)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-400
                     hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
          title="Exit admin panel"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard
          title="Recommendations Today"
          value={s.total_recommendations_today ?? 0}
          icon={Activity}
          color="cyan"
        />
        <KPICard
          title="Total Users"
          value={s.total_users ?? 0}
          icon={Users}
          color="violet"
        />
        <KPICard
          title="Avg Confidence Score"
          value={s.avg_confidence_score ?? 0}
          unit="%"
          icon={BarChart3}
          color="amber"
          decimals={1}
        />
        <KPICard
          title="Estimated API Cost Today"
          value={s.estimated_api_cost_today_usd ?? 0}
          prefix="$"
          icon={DollarSign}
          color="green"
          decimals={4}
        />
      </div>

      {/* Model metrics banner */}
      <div className="card p-4 mb-6 flex flex-wrap items-center gap-6">
        <div className="flex flex-col">
          <span className="text-slate-500 text-xs uppercase tracking-wide">Model NDCG@10</span>
          <span className="text-cyan-400 font-bold text-xl">
            {s.model_ndcg_score > 0 ? s.model_ndcg_score.toFixed(4) : 'Run training'}
          </span>
        </div>
        <div className="w-px h-8 bg-slate-700 hidden sm:block" />
        <div className="flex flex-col">
          <span className="text-slate-500 text-xs uppercase tracking-wide">Top Category</span>
          <span className="text-slate-100 font-bold text-xl">{s.top_category ?? '—'}</span>
        </div>
        <div className="w-px h-8 bg-slate-700 hidden sm:block" />
        <div className="flex flex-col">
          <span className="text-slate-500 text-xs uppercase tracking-wide">Cache Utilisation</span>
          <span className="text-emerald-400 font-bold text-xl">
            {s.cache_hit_rate != null ? `${s.cache_hit_rate}%` : '—'}
          </span>
        </div>
        <div className="ml-auto hidden lg:flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-emerald-400 text-xs">System healthy</span>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <SectionCard title="Global Feature Importance" className="lg:col-span-2">
          {importance.isLoading ? (
            <div className="h-64 flex items-center justify-center text-slate-500">
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : (
            <FeatureImportanceChart features={imp.features || []} />
          )}
        </SectionCard>

        <SectionCard title="Category Distribution">
          <CategoryPie />
        </SectionCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectionCard title="Recommendations Over Time (7 days)">
          {performance.isLoading ? (
            <div className="h-48 flex items-center justify-center text-slate-500">
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : (
            <RecommendationsOverTime days={perf.days || []} />
          )}
        </SectionCard>

        <SectionCard title="Daily Performance">
          {performance.isLoading ? (
            <div className="h-48 flex items-center justify-center text-slate-500">
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : (
            <ModelPerformanceTable days={perf.days || []} />
          )}
        </SectionCard>
      </div>
    </motion.div>
  )
}
