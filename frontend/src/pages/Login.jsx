import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LogIn, Loader2, AlertCircle } from 'lucide-react'
import { loginUser } from '../services/api'
import useAppStore from '../store/appStore'

export default function Login() {
  const navigate = useNavigate()
  const login = useAppStore((s) => s.login)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginUser(email, password)
      login(
        { email, name: data.name, is_admin: data.is_admin, user_id: data.user_id },
        data.access_token
      )
      navigate('/')
    } catch (err) {
      setError(err.message || 'Login failed')
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
          <h1 className="text-3xl font-bold text-slate-100 dark:text-slate-100 mt-2">
            Sign in
          </h1>
          <p className="text-slate-400 text-sm mt-2">
            Enter your credentials to access recommendations
          </p>
        </div>

        {/* Card */}
        <div className="card p-8">
          {error && (
            <div className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3 mb-5 text-sm">
              <AlertCircle size={16} className="shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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
                <LogIn size={16} />
              )}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-center text-slate-500 text-sm mt-6">
            No account?{' '}
            <Link to="/register" className="text-cyan-400 hover:text-cyan-300 transition-colors">
              Register here
            </Link>
          </p>
        </div>

        {/* Demo hint */}
        <div className="mt-4 card p-4">
          <p className="text-slate-500 text-xs text-center mb-2 font-medium uppercase tracking-wide">
            Demo credentials
          </p>
          <div className="space-y-1.5 text-xs text-slate-400 text-center">
            <p><span className="text-slate-300">tech@demo.xai</span> · Demo1234!</p>
            <p><span className="text-slate-300">books@demo.xai</span> · Demo1234!</p>
            <p><span className="text-slate-300">fashion@demo.xai</span> · Demo1234!</p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
