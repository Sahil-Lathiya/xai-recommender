import { AnimatePresence, motion } from 'framer-motion'
import { X, Bot, Cpu, AlertCircle, Loader2, ArrowLeft, ExternalLink } from 'lucide-react'
import { useExplanation } from '../../hooks/useExplanation'
import CounterfactualCard from './CounterfactualCard'
import SHAPWaterfall from '../Charts/SHAPWaterfall'
import useAppStore from '../../store/appStore'

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

function MatchBadge({ score }) {
  const color = score >= 80 ? '#00B4D8' : score >= 60 ? '#F59E0B' : '#EF4444'
  const label = score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : 'Fair'
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl bg-slate-800/60 border border-slate-700/50">
      <div className="text-4xl font-bold tabular-nums" style={{ color }}>
        {score}%
      </div>
      <div>
        <p className="text-slate-100 font-semibold text-sm">{label} match</p>
        <p className="text-slate-500 text-xs mt-0.5">Overall recommendation confidence</p>
      </div>
    </div>
  )
}

function PanelContent({ recommendationId, onClose }) {
  const { data, isLoading, isError, error } = useExplanation(recommendationId)

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-400">
        <Loader2 size={28} className="animate-spin text-cyan-400" />
        <p className="text-sm">Generating explanation…</p>
        <p className="text-xs text-slate-500">Running SHAP + GPT-4o-mini</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-48 gap-3 text-slate-400">
        <AlertCircle size={28} className="text-red-400" />
        <p className="text-sm">{error?.message || 'Could not load explanation'}</p>
      </div>
    )
  }

  if (!data) return null

  const { product, shap_values, llm_explanation, counterfactual, confidence_score } = data
  const amazonUrl = product.amazon_url || `https://www.amazon.co.uk/s?k=${encodeURIComponent(product.name)}`
  const categoryColor = CATEGORY_COLORS[product.category] || 'bg-slate-600/20 text-slate-400 border-slate-600/30'
  const fallbackEmoji = CATEGORY_EMOJI[product.category] || '📦'

  return (
    <div className="flex flex-col gap-5">
      {/* Back link */}
      <button
        onClick={onClose}
        className="flex items-center gap-1.5 text-slate-400 hover:text-slate-100
                   text-sm transition-colors w-fit -mt-1"
      >
        <ArrowLeft size={15} />
        Back to Recommendations
      </button>

      {/* Product image (large) */}
      <a href={amazonUrl} target="_blank" rel="noopener noreferrer" className="block">
        <div className="relative w-full h-52 overflow-hidden rounded-xl bg-slate-700">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
              onError={(e) => {
                e.target.style.display = 'none'
                e.target.nextSibling.style.display = 'flex'
              }}
            />
          ) : null}
          <div
            className="w-full h-full flex items-center justify-center text-6xl"
            style={{ display: product.image_url ? 'none' : 'flex' }}
          >
            {fallbackEmoji}
          </div>
        </div>
      </a>

      {/* Product name + category */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className={`badge border text-xs ${categoryColor}`}>
            {product.category}
          </span>
          <span className="text-slate-500 text-xs">£{product.price.toFixed(2)}</span>
        </div>
        <h3 className="text-slate-100 font-bold text-base leading-snug">
          {product.name}
        </h3>
      </div>

      {/* Match score — prominent */}
      <MatchBadge score={confidence_score} />

      {/* LLM explanation */}
      <div className="rounded-xl border border-blue-400/30 bg-blue-400/5 p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-7 h-7 rounded-lg bg-blue-400/15 flex items-center justify-center">
            <Bot size={14} className="text-blue-400" />
          </div>
          <span className="text-blue-300 text-xs font-semibold uppercase tracking-wide">
            Why this was recommended
          </span>
          <span className="ml-auto badge bg-blue-400/10 text-blue-400 border border-blue-400/20 text-xs">
            GPT-4o-mini
          </span>
        </div>
        <p className="text-slate-200 text-sm leading-relaxed">{llm_explanation}</p>
      </div>

      {/* SHAP chart — top 5 features, human labels */}
      <div>
        <h4 className="text-slate-300 text-xs font-semibold uppercase tracking-wide mb-3">
          What drove this recommendation
        </h4>
        <SHAPWaterfall contributions={shap_values?.feature_contributions || []} limit={5} />
      </div>

      {/* Counterfactual */}
      <CounterfactualCard text={counterfactual} />

      {/* View on Amazon */}
      <a
        href={amazonUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 w-full py-3 rounded-xl
                   bg-amber-400/10 border border-amber-400/30 text-amber-400
                   font-semibold text-sm hover:bg-amber-400/20 hover:border-amber-400/60
                   transition-colors duration-200"
      >
        View on Amazon
        <ExternalLink size={14} />
      </a>

      {/* Footer */}
      <div className="flex items-center justify-center gap-2 pt-1 border-t border-slate-700/50">
        <Cpu size={12} className="text-slate-500" />
        <span className="text-slate-500 text-xs">
          {data.powered_by || 'XGBoost + SHAP + GPT-4o-mini'}
        </span>
      </div>
    </div>
  )
}

export default function ExplanationPanel() {
  const openExplanationId = useAppStore((s) => s.openExplanationId)
  const closeExplanation = useAppStore((s) => s.closeExplanation)
  const isOpen = !!openExplanationId

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeExplanation}
          />

          {/* Panel */}
          <motion.aside
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md
                       bg-slate-900 border-l border-slate-700/60
                       shadow-2xl flex flex-col"
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* Panel header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-slate-100 font-semibold text-sm">
                  Why was this recommended?
                </span>
              </div>
              <button
                onClick={closeExplanation}
                className="p-1.5 text-slate-400 hover:text-slate-100
                           hover:bg-slate-700/50 rounded-lg transition-colors"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto px-5 py-5">
              <PanelContent recommendationId={openExplanationId} onClose={closeExplanation} />
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
