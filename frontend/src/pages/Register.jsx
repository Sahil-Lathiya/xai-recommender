import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { UserPlus, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { registerUser } from '../services/api'

export default function Register() {
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await registerUser(name, email, password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <motion.div
        className="w-full max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Header */}
        <div className="text-center mb-8">
          <span className="badge bg-cyan-400/10 text-cyan-400 border border-cyan-400/20 text-xs mb-4">
            XAI Recommender
          </span>
          <h1 className="text-3xl font-bold text-slate-100 mt-2">
            Create account
          </h1>
          <p className="text-slate-400 text-sm mt-2">
            Start getting explainable AI recommendations
          </p>
        </div>

        {/* Card */}
        <div className="card p-8">
          {success ? (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <CheckCircle size={40} className="text-emerald-400" />
              <p className="text-slate-100 font-semibold">Account created!</p>
              <p className="text-slate-400 text-sm">Redirecting to login…</p>
            </div>
          ) : (
            <>
              {error && (
                <div className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3 mb-5 text-sm">
                  <AlertCircle size={16} className="shrink-0" />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-slate-300 text-sm font-medium mb-1.5">
                    Name
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Your name"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-2.5
                               text-slate-100 placeholder-slate-500 text-sm
                               focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50
                               transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 text-sm font-medium mb-1.5">
                    Email
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-2.5
                               text-slate-100 placeholder-slate-500 text-sm
                               focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50
                               transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 text-sm font-medium mb-1.5">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-4 py-2.5
                               text-slate-100 placeholder-slate-500 text-sm
                               focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50
                               transition-colors"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 btn-primary py-2.5 mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <UserPlus size={16} />
                  )}
                  {loading ? 'Creating account…' : 'Create account'}
                </button>
              </form>

              <p className="text-center text-slate-500 text-sm mt-6">
                Already have an account?{' '}
                <Link to="/login" className="text-cyan-400 hover:text-cyan-300 transition-colors">
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  )
}
