import { motion } from 'framer-motion'
import { Star, Zap } from 'lucide-react'
import { clsx } from 'clsx'
import useAppStore from '../../store/appStore'
import { useTrackAndRefresh } from '../../hooks/useTrackAndRefresh'

const CATEGORY_COLORS = {
  Electronics: 'bg-cyan-400/15 text-cyan-400 border-cyan-400/30',
  Books:       'bg-violet-400/15 text-violet-400 border-violet-400/30',
  Clothing:    'bg-pink-400/15 text-pink-400 border-pink-400/30',
  Home:        'bg-amber-400/15 text-amber-400 border-amber-400/30',
}

const CATEGORY_EMOJI = {
  Electronics: '📱',
  Books:       '📚',
  Clothing:    '👗',
  Home:        '🏠',
}

function StarRating({ rating }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={13}
          className={
            star <= Math.round(rating)
              ? 'text-amber-400 fill-amber-400'
              : 'text-slate-600'
          }
        />
      ))}
      <span className="text-slate-400 text-xs ml-1">{rating.toFixed(1)}</span>
    </div>
  )
}

function ConfidencePill({ score }) {
  const color =
    score >= 80
      ? 'bg-cyan-400/15 text-cyan-400 border-cyan-400/30'
      : score >= 60
      ? 'bg-amber-400/15 text-amber-400 border-amber-400/30'
      : 'bg-slate-600/30 text-slate-400 border-slate-600/30'

  return (
    <span className={clsx('badge border text-xs font-semibold', color)}>
      {score}% match
    </span>
  )
}

export default function ProductCard({ recommendation, onExplain }) {
  const { product, score, confidence_score, top_reason, recommendation_id } =
    recommendation

  const loggedInUser = useAppStore((s) => s.loggedInUser)
  const currentUser  = useAppStore((s) => s.currentUser)
  const accessToken  = useAppStore((s) => s.accessToken)

  // Resolve active user: prefer logged-in user, fall back to demo selector
  const userId = loggedInUser?.user_id ?? currentUser?.id ?? null
  const token  = accessToken ?? null

  const trackAndRefresh = useTrackAndRefresh(userId, token)

  const categoryColor =
    CATEGORY_COLORS[product.category] ||
    'bg-slate-600/20 text-slate-400 border-slate-600/30'

  const fallbackEmoji = CATEGORY_EMOJI[product.category] || '📦'
  const amazonUrl = product.amazon_url || null

  function handleWhyClick() {
    onExplain(recommendation_id, product.id)
    trackAndRefresh(product.id, 'click')
  }

  function handleBuyClick() {
    trackAndRefresh(product.id, 'click')
  }

  return (
    <motion.div
      className="card p-5 flex flex-col gap-3 cursor-default"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, boxShadow: '0 8px 32px -4px rgba(0,180,216,0.15)' }}
      transition={{ duration: 0.25 }}
    >
      {/* Product image */}
      <div className="relative w-full h-44 overflow-hidden rounded-lg bg-slate-700 dark:bg-slate-700">
        <img
          src={product.image_url || '/placeholder-product.svg'}
          alt={product.name}
          className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
          loading="lazy"
          onError={(e) => {
            e.target.onerror = null
            e.target.src = '/placeholder-product.svg'
          }}
        />
        <div className="absolute top-2 right-2">
          <ConfidencePill score={confidence_score} />
        </div>
      </div>

      {/* Category + price */}
      <div className="flex items-center justify-between">
        <span className={clsx('badge border text-xs', categoryColor)}>
          {product.category}
        </span>
        <span className="text-slate-100 font-bold text-lg">
          £{product.price != null ? product.price.toFixed(2) : 'N/A'}
        </span>
      </div>

      {/* Product name */}
      <p className="text-slate-100 font-semibold text-sm leading-snug line-clamp-2">
        {product.name}
      </p>

      {/* Rating + review count */}
      <div className="flex items-center justify-between">
        <StarRating rating={product.rating} />
        <span className="text-slate-500 text-xs">
          {product.review_count?.toLocaleString()} reviews
        </span>
      </div>

      {/* Top reason teaser */}
      {top_reason && (
        <p className="text-slate-400 text-xs leading-relaxed line-clamp-2 border-l-2 border-cyan-400/40 pl-2">
          {top_reason}
        </p>
      )}

      {/* Action row */}
      <div className="mt-auto flex flex-col gap-2">
        {/* Why Recommended? */}
        <motion.button
          onClick={handleWhyClick}
          className="flex items-center justify-center gap-2 w-full py-2 rounded-lg
                     bg-cyan-400/10 border border-cyan-400/30 text-cyan-400 text-sm font-medium
                     hover:bg-cyan-400/20 hover:border-cyan-400/60 transition-colors duration-200"
          whileTap={{ scale: 0.97 }}
        >
          <Zap size={14} />
          Why Recommended?
        </motion.button>

        {/* Buy on Amazon — only shown if URL exists */}
        {amazonUrl && (
          <a
            href={amazonUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleBuyClick}
            className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg
                       text-sm font-semibold text-white transition-opacity hover:opacity-90"
            style={{ backgroundColor: '#FF9900' }}
          >
            Buy on Amazon ↗
          </a>
        )}
      </div>
    </motion.div>
  )
}
