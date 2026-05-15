import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Moon, Sun, LogOut } from 'lucide-react'
import { clsx } from 'clsx'
import useAppStore from '../../store/appStore'

function XAILogo() {
  return (
    <svg
      width="148"
      height="28"
      viewBox="0 0 148 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="XAI Recommender"
    >
      {/* X mark — two crossing strokes */}
      <line x1="3"  y1="5"  x2="19" y2="23" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="19" y1="5"  x2="3"  y2="23" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      {/* AI node at the crossing point — teal fill with white centre */}
      <circle cx="11" cy="14" r="4"   fill="#01696f" />
      <circle cx="11" cy="14" r="1.8" fill="white"   />
      {/* Brand name */}
      <text
        x="28" y="20"
        fontFamily="Inter, system-ui, -apple-system, sans-serif"
        fontWeight="700"
        fontSize="15"
        fill="currentColor"
      >XAI</text>
      <text
        x="60" y="20"
        fontFamily="Inter, system-ui, -apple-system, sans-serif"
        fontWeight="400"
        fontSize="12"
        fill="currentColor"
        opacity="0.5"
      >Recommender</text>
    </svg>
  )
}

function UserAvatar({ name }) {
  const initials = name
    ? name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
    : '?'
  return (
    <div className="w-7 h-7 rounded-full bg-cyan-400/20 border border-cyan-400/40
                    flex items-center justify-center flex-shrink-0">
      <span className="text-cyan-400 text-xs font-bold leading-none">{initials}</span>
    </div>
  )
}

export default function Navbar() {
  const location    = useLocation()
  const navigate    = useNavigate()
  const darkMode    = useAppStore((s) => s.darkMode)
  const toggleDarkMode = useAppStore((s) => s.toggleDarkMode)
  const loggedInUser   = useAppStore((s) => s.loggedInUser)
  const logout         = useAppStore((s) => s.logout)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const navLink = (to, label) => (
    <Link
      key={to}
      to={to}
      className={clsx(
        'text-sm font-medium transition-colors duration-200 px-3 py-1.5 rounded-lg',
        location.pathname === to
          ? 'text-cyan-400 bg-cyan-400/10'
          : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-700/50'
      )}
    >
      {label}
    </Link>
  )

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-16
                    bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm
                    border-b border-slate-200 dark:border-slate-700/50
                    transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center shrink-0">
          <XAILogo />
        </Link>

        {/* Centre nav — Recommendations only when logged in; Admin Panel always visible */}
        <div className="flex items-center gap-1">
          {loggedInUser && navLink('/', 'Recommendations')}
          {navLink('/dashboard', 'Admin Panel')}
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleDarkMode}
            className="p-2 text-slate-400 hover:text-slate-700 dark:hover:text-slate-100
                       hover:bg-slate-100 dark:hover:bg-slate-700/50 rounded-lg transition-colors"
            aria-label="Toggle dark mode"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {loggedInUser ? (
            <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-slate-700 ml-1">
              <Link
                to="/profile"
                className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                title="View profile"
              >
                <UserAvatar name={loggedInUser.name} />
                <span className="hidden sm:inline text-sm text-slate-600 dark:text-slate-300 font-medium max-w-[120px] truncate">
                  {loggedInUser.name?.split(' ')[0] || 'Profile'}
                </span>
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-sm
                           text-slate-500 dark:text-slate-400
                           hover:text-red-400 hover:bg-red-400/10
                           rounded-lg transition-colors"
                title="Sign out"
              >
                <LogOut size={15} />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="px-3 py-1.5 text-sm font-medium text-cyan-400 hover:bg-cyan-400/10 rounded-lg transition-colors"
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </nav>
  )
}
