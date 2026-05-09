import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Activity, Users, BarChart3, DollarSign,
  Loader2, AlertCircle, ShieldAlert, ArrowLeft,
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

const PAGE_VARIANTS = {
  hidden: { opacity: 0, y: 20 },
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

function AdminRequired() {
  return (
    <motion.div
      className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 rounded-full bg-amber-400/10 border border-amber-400/20
                        flex items-center justify-center mx-auto mb-5">
          <ShieldAlert size={30} className="text-amber-400" />
        </div>
        <h1 className="text-xl font-bold text-slate-100 mb-2">
          Admin Access Required
        </h1>
        <p className="text-slate-400 text-sm leading-relaxed mb-6">
          The dashboard contains system metrics, model performance data, and
          API cost information restricted to administrators only.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 btn-primary"
        >
          <ArrowLeft size={15} />
          Back to Recommendations
        </Link>
      </div>
    </motion.div>
  )
}

export default function Dashboard() {
  const loggedInUser = useAppStore((s) => s.loggedInUser)

  if (!loggedInUser?.is_admin) {
    return <AdminRequired />
  }

  const stats = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
  })

  const performance = useQuery({
    queryKey: ['model-performance'],
    queryFn: getModelPerformance,
    staleTime: 60_000,
  })

  const importance = useQuery({
    queryKey: ['global-feature-importance'],
    queryFn: getGlobalFeatureImportance,
    staleTime: 3_600_000,
  })

  if (stats.isLoading) return <LoadingState />
  if (stats.isError) return <ErrorState message={stats.error?.message} />

  const s = stats.data || {}
  const perf = performance.data || {}
  const imp = importance.data || {}

  return (
    <motion.div
      className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10"
      variants={PAGE_VARIANTS}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <div className="mb-8">
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
