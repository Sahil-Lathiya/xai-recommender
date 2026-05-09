import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react'
import { useExplanation } from '../hooks/useExplanation'
import ConfidenceRing from '../components/ExplanationPanel/ConfidenceRing'
import CounterfactualCard from '../components/ExplanationPanel/CounterfactualCard'
import SHAPWaterfall from '../components/Charts/SHAPWaterfall'

const PAGE_VARIANTS = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4 } },
}

export default function ProductDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useExplanation(id)

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <Loader2 size={32} className="animate-spin text-cyan-400" />
        <p className="text-sm">Loading product explanation…</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-slate-400">
        <AlertCircle size={36} className="text-red-400" />
        <p className="text-slate-300 font-medium">Explanation not found</p>
        <p className="text-sm text-slate-500">{error?.message}</p>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm transition-colors"
        >
          Back to recommendations
        </button>
      </div>
    )
  }

  if (!data) return null
  const { product, shap_values, llm_explanation, counterfactual, confidence_score } = data

  return (
    <motion.div
      className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10"
      variants={PAGE_VARIANTS}
      initial="hidden"
      animate="visible"
    >
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-slate-400 hover:text-slate-100 text-sm mb-6 transition-colors"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      {/* Product hero */}
      <div className="card p-6 mb-6 flex flex-col sm:flex-row gap-6">
        {product.image_url && (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full sm:w-48 h-48 object-cover rounded-xl bg-slate-700 flex-shrink-0"
          />
        )}
        <div className="flex flex-col justify-center gap-3">
          <span className="badge bg-cyan-400/10 text-cyan-400 border border-cyan-400/20 text-xs w-fit">
            {product.category}
          </span>
          <h1 className="text-slate-100 font-bold text-xl leading-snug">{product.name}</h1>
          <p className="text-cyan-400 font-bold text-2xl">£{product.price.toFixed(2)}</p>
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span>⭐ {product.rating.toFixed(1)}/5</span>
            <span>·</span>
            <span>{product.review_count.toLocaleString()} reviews</span>
          </div>
        </div>
        <div className="sm:ml-auto flex-shrink-0 flex items-center justify-center">
          <ConfidenceRing score={confidence_score} size={120} />
        </div>
      </div>

      {/* LLM explanation */}
      <div className="card p-5 mb-4 border-blue-400/20 bg-blue-400/5">
        <p className="text-blue-300 text-xs font-semibold uppercase tracking-wide mb-3">
          🤖 AI Explanation (GPT-4o-mini)
        </p>
        <p className="text-slate-200 text-sm leading-relaxed">{llm_explanation}</p>
      </div>

      {/* SHAP waterfall */}
      <div className="card p-5 mb-4">
        <h3 className="text-slate-300 text-sm font-semibold uppercase tracking-wide mb-4">
          Feature Contributions (SHAP)
        </h3>
        <SHAPWaterfall contributions={shap_values?.feature_contributions || []} />
      </div>

      {/* Counterfactual */}
      <CounterfactualCard text={counterfactual} />

      {/* Footer */}
      <p className="text-center text-slate-600 text-xs mt-6">
        Powered by XGBoost + SHAP + GPT-4o-mini
      </p>
    </motion.div>
  )
}
