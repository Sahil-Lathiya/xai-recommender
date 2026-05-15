import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { ArrowLeft, Star, Package, BarChart3, Clock, AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { getUserProfile } from '../services/api'
import useAppStore from '../store/appStore'

const CATEGORY_COLORS = {
  Electronics: 'bg-cyan-400/15 text-cyan-400 border-cyan-400/30',
  Books: 'bg-violet-400/15 text-violet-400 border-violet-400/30',
  Clothing: 'bg-pink-400/15 text-pink-400 border-pink-400/30',
  Home: 'bg-amber-400/15 text-amber-400 border-amber-400/30',
}

const CATEGORY_EMOJI = {
  Electronics: '📱',
  Books: '📚',
  Clothing: '👗',
  Home: '🏠',
}

const CATEGORY_BAR = {
  Electronics: 'bg-cyan-400',
  Books: 'bg-violet-400',
  Clothing: 'bg-pink-400',
  Home: 'bg-amber-400',
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'long', year: 'numeric',
  })
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const seconds = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (seconds < 60)  return 'just now'
  const mins = Math.floor(seconds / 60)
  if (mins < 60)     return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24)    return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const ACTION_LABELS = {
  view:     { label: 'Viewed',   color: 'bg-slate-600/20 text-slate-400 border-slate-600/30' },
  click:    { label: 'Explored', color: 'bg-cyan-400/15 text-cyan-400 border-cyan-400/30' },
  purchase: { label: 'Bought',   color: 'bg-emerald-400/15 text-emerald-400 border-emerald-400/30' },
  rate:     { label: 'Rated',    color: 'bg-amber-400/15 text-amber-400 border-amber-400/30' },
}

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

function StatCard({ icon: Icon, label, value, colorClass }) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colorClass}`}>
        <Icon size={16} />
      </div>
      <div>
        <p className="text-slate-500 dark:text-slate-500 text-xs">{label}</p>
        <p className="text-slate-900 dark:text-slate-100 font-bold text-sm">{value}</p>
      </div>
    </div>
  )
}

function BackLink() {
  return (
    <Link
      to="/"
      className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400
                 hover:text-slate-900 dark:hover:text-slate-100
                 text-sm mb-6 w-fit transition-colors"
    >
      <ArrowLeft size={15} />
      Back to Recommendations
    </Link>
  )
}

/* Shown when profile API can't load but user is logged in */
function StaleSessionFallback({ user }) {
  return (
    <motion.div
      className="max-w-3xl mx-auto px-4 sm:px-6 py-10"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <BackLink />
      <div className="card p-6 mb-5 flex items-center gap-5">
        <div className="w-20 h-20 rounded-full bg-cyan-400/20 border-2 border-cyan-400/40
                        flex items-center justify-center flex-shrink-0">
          <span className="text-3xl font-bold text-cyan-400">{getInitials(user.name)}</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{user.name || 'User'}</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">{user.email}</p>
        </div>
      </div>
      <div className="card p-8 text-center">
        <AlertCircle size={28} className="text-amber-400 mx-auto mb-3" />
        <p className="text-slate-700 dark:text-slate-300 font-medium text-sm mb-1">
          Profile details couldn't be loaded
        </p>
        <p className="text-slate-500 dark:text-slate-500 text-xs mb-4">
          Sign out and sign back in to refresh your session.
        </p>
        <Link
          to="/login"
          className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-400/10 text-cyan-400
                     border border-cyan-400/30 rounded-lg text-sm font-medium hover:bg-cyan-400/20 transition-colors"
        >
          <RefreshCw size={14} />
          Sign in again
        </Link>
      </div>
    </motion.div>
  )
}

export default function Profile() {
  const loggedInUser = useAppStore((s) => s.loggedInUser)

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['user-profile-detail', loggedInUser?.user_id],
    queryFn: () => getUserProfile(loggedInUser?.user_id),
    enabled: !!loggedInUser?.user_id,
    staleTime: 30_000,
    retry: 1,
  })

  if (!loggedInUser) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-3 text-slate-500">
        <AlertCircle size={28} className="text-amber-400" />
        <p className="text-sm">Please sign in to view your profile.</p>
        <Link to="/login" className="btn-primary mt-2">Sign in</Link>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-3 text-slate-500">
        <Loader2 size={28} className="animate-spin text-cyan-400" />
        <p className="text-sm">Loading your profile…</p>
      </div>
    )
  }

  /* Guard: query disabled (no user_id in session) or returned null */
  if (!data && !isError) {
    return <StaleSessionFallback user={loggedInUser} />
  }

  if (isError || !data) {
    return (
      <motion.div
        className="max-w-3xl mx-auto px-4 sm:px-6 py-10"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <BackLink />
        <div className="card p-8 text-center">
          <AlertCircle size={28} className="text-red-400 mx-auto mb-3" />
          <p className="text-slate-700 dark:text-slate-300 font-medium text-sm mb-1">
            {error?.message || 'Could not load profile'}
          </p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-400/10 text-cyan-400
                       border border-cyan-400/30 rounded-lg text-sm font-medium hover:bg-cyan-400/20
                       transition-colors mt-4"
          >
            <RefreshCw size={14} />
            Try again
          </button>
        </div>
      </motion.div>
    )
  }

  const profile = data
  const initials = getInitials(profile.name)
  const favEmoji = CATEGORY_EMOJI[profile.favourite_category] || '🛍️'
  const favLabel = profile.favourite_category
    ? `${favEmoji} ${profile.favourite_category} lover`
    : '🔍 Still discovering your taste'

  const ratingComment =
    profile.avg_rating_given >= 4.5 ? 'you have high standards'
    : profile.avg_rating_given >= 4.0 ? 'you appreciate quality'
    : 'you rate candidly'

  return (
    <motion.div
      className="max-w-3xl mx-auto px-4 sm:px-6 py-10"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <BackLink />

      {/* Header card */}
      <div className="card p-6 mb-5 flex items-center gap-5">
        <div className="w-20 h-20 rounded-full bg-cyan-400/20 border-2 border-cyan-400/40
                        flex items-center justify-center flex-shrink-0">
          <span className="text-3xl font-bold text-cyan-400">{initials}</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{profile.name}</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5">{profile.email}</p>
          <p className="text-slate-400 dark:text-slate-500 text-xs mt-1">
            Member since {formatDate(profile.created_at)}
          </p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5">
        <StatCard
          icon={Package}
          label="Products explored"
          value={profile.total_interactions.toLocaleString()}
          colorClass="bg-cyan-400/10 text-cyan-400"
        />
        <StatCard
          icon={Star}
          label="Avg rating given"
          value={profile.avg_rating_given != null ? `${profile.avg_rating_given}★` : '—'}
          colorClass="bg-amber-400/10 text-amber-400"
        />
        <StatCard
          icon={BarChart3}
          label="Recommendations received"
          value={profile.total_recommendations.toLocaleString()}
          colorClass="bg-violet-400/10 text-violet-400"
        />
      </div>

      {/* Taste Profile */}
      <div className="card p-5 mb-5">
        <h2 className="text-slate-600 dark:text-slate-300 text-sm font-semibold uppercase tracking-wide mb-4">
          Your Taste Profile
        </h2>
        <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-100 dark:bg-slate-800/60
                        border border-slate-200 dark:border-slate-700/50 mb-3">
          <span className="text-2xl">{favEmoji}</span>
          <div>
            <p className="text-slate-900 dark:text-slate-100 font-semibold text-sm">{favLabel}</p>
            <p className="text-slate-500 dark:text-slate-500 text-xs mt-0.5">Based on your interaction history</p>
          </div>
        </div>
        {profile.avg_rating_given != null ? (
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            You rate products{' '}
            <span className="text-amber-500 dark:text-amber-400 font-semibold">{profile.avg_rating_given}★</span>
            {' '}on average — {ratingComment}.
          </p>
        ) : (
          <p className="text-slate-400 dark:text-slate-500 text-sm italic">
            Start exploring products to build your taste profile.
          </p>
        )}
      </div>

      {/* Category breakdown */}
      {Object.keys(profile.category_distribution).length > 0 && (
        <div className="card p-5 mb-5">
          <h2 className="text-slate-600 dark:text-slate-300 text-sm font-semibold uppercase tracking-wide mb-4">
            Recommendation Breakdown
          </h2>
          <p className="text-slate-400 dark:text-slate-500 text-xs mb-4">
            {profile.total_recommendations} total recommendations across categories
          </p>
          <div className="space-y-3">
            {Object.entries(profile.category_distribution).map(([cat, pct]) => (
              <div key={cat}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-700 dark:text-slate-300 text-xs font-medium">
                    {CATEGORY_EMOJI[cat] || '📦'} {cat}
                  </span>
                  <span className="text-slate-500 dark:text-slate-400 text-xs font-semibold">{pct}%</span>
                </div>
                <div className="w-full h-2 bg-slate-200 dark:bg-slate-700/50 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${CATEGORY_BAR[cat] || 'bg-slate-400'}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.8, delay: 0.2, ease: 'easeOut' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recently Explored */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={14} className="text-slate-400 dark:text-slate-500" />
          <h2 className="text-slate-600 dark:text-slate-300 text-sm font-semibold uppercase tracking-wide">
            Recently Explored
          </h2>
        </div>
        {profile.recent_explorations.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-4xl mb-3">🔍</p>
            <p className="text-slate-600 dark:text-slate-400 font-medium text-sm">No activity yet</p>
            <p className="text-slate-400 dark:text-slate-500 text-xs mt-1 max-w-xs mx-auto">
              Click &quot;Why Recommended?&quot; or &quot;Buy on Amazon&quot; on any product to start your history
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {profile.recent_explorations.map((item, i) => {
              const action = ACTION_LABELS[item.action_type] || ACTION_LABELS.view
              return (
                <motion.div
                  key={item.id}
                  className="flex items-center gap-3 p-3 rounded-lg
                             bg-slate-50 dark:bg-slate-800/40
                             border border-slate-200 dark:border-slate-700/30"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  {/* Thumbnail */}
                  <div className="w-11 h-11 rounded-lg overflow-hidden bg-slate-200 dark:bg-slate-700 flex-shrink-0">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.product_name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.onerror = null
                          e.target.style.display = 'none'
                          e.target.parentNode.textContent = CATEGORY_EMOJI[item.product_category] || '📦'
                        }}
                      />
                    ) : (
                      <span className="w-full h-full flex items-center justify-center text-lg">
                        {CATEGORY_EMOJI[item.product_category] || '📦'}
                      </span>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-slate-900 dark:text-slate-100 text-sm font-medium truncate">
                      {item.product_name}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className={`badge border text-xs ${CATEGORY_COLORS[item.product_category] || 'bg-slate-600/20 text-slate-400 border-slate-600/30'}`}>
                        {item.product_category}
                      </span>
                      <span className={`badge border text-xs ${action.color}`}>
                        {action.label}
                      </span>
                      <span className="text-slate-400 dark:text-slate-500 text-xs">
                        {timeAgo(item.timestamp)}
                      </span>
                    </div>
                  </div>

                  {/* Buy link */}
                  {item.amazon_url && (
                    <a
                      href={item.amazon_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-shrink-0 px-2.5 py-1 text-xs font-semibold text-white rounded-md
                                 hover:opacity-90 transition-opacity"
                      style={{ backgroundColor: '#FF9900' }}
                    >
                      Buy ↗
                    </a>
                  )}
                </motion.div>
              )
            })}
          </div>
        )}
      </div>
    </motion.div>
  )
}
