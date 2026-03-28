import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-culpa-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <img src="/culpa-logo.svg" alt="Culpa" className="h-12 w-12 mb-4" />
          <span className="font-mono font-bold text-2xl text-culpa-text tracking-tight">culpa</span>
          <p className="text-sm text-culpa-text-dim mt-1">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-culpa-surface border border-culpa-border rounded-2xl p-6 space-y-4">
          {error && (
            <div className="bg-culpa-red-dim border border-culpa-red/30 text-culpa-red text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs text-culpa-text-dim mb-1.5">Email</label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 bg-culpa-bg border border-culpa-border rounded-lg
                         text-sm text-culpa-text placeholder:text-culpa-text-dim
                         focus:outline-none focus:ring-2 focus:ring-culpa-red/30 focus:border-culpa-red/50
                         transition-colors"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-xs text-culpa-text-dim mb-1.5">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 bg-culpa-bg border border-culpa-border rounded-lg
                         text-sm text-culpa-text placeholder:text-culpa-text-dim
                         focus:outline-none focus:ring-2 focus:ring-culpa-red/30 focus:border-culpa-red/50
                         transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-culpa-red hover:bg-culpa-red/80 text-white font-medium text-sm
                       rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>

          <p className="text-center text-xs text-culpa-text-dim">
            Don't have an account?{' '}
            <Link to="/register" className="text-culpa-red hover:text-culpa-red/80 transition-colors">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
