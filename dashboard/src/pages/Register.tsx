import React, { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { cn } from '../lib/utils'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

function PasswordChecklist({ password }: { password: string }) {
  const checks = [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'One uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'One lowercase letter', met: /[a-z]/.test(password) },
    { label: 'One number', met: /[0-9]/.test(password) },
  ]

  return (
    <div className="space-y-1 mt-1.5">
      {checks.map((c) => (
        <div key={c.label} className="flex items-center gap-1.5 text-[11px]">
          {c.met
            ? <Check size={10} className="text-culpa-green" />
            : <X size={10} className="text-culpa-text-dim/40" />
          }
          <span className={c.met ? 'text-culpa-green' : 'text-culpa-text-dim/60'}>
            {c.label}
          </span>
        </div>
      ))}
    </div>
  )
}

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [emailTouched, setEmailTouched] = useState(false)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const emailValid = EMAIL_REGEX.test(email)
  const passwordValid = useMemo(() => (
    password.length >= 8 &&
    /[A-Z]/.test(password) &&
    /[a-z]/.test(password) &&
    /[0-9]/.test(password)
  ), [password])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!emailValid) {
      setError('Please enter a valid email address')
      return
    }
    if (!passwordValid) {
      setError('Password does not meet all requirements')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await register(email, password, name || undefined)
      navigate('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed')
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
          <p className="text-sm text-culpa-text-dim mt-1">Create your account</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-culpa-surface border border-culpa-border rounded-2xl p-6 space-y-4">
          {error && (
            <div className="bg-culpa-red-dim border border-culpa-red/30 text-culpa-red text-sm px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs text-culpa-text-dim mb-1.5">Name <span className="text-culpa-text-dim/50">(optional)</span></label>
            <input
              type="text"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2.5 bg-culpa-bg border border-culpa-border rounded-lg
                         text-sm text-culpa-text placeholder:text-culpa-text-dim
                         focus:outline-none focus:ring-2 focus:ring-culpa-red/30 focus:border-culpa-red/50
                         transition-colors"
              placeholder="Your name"
            />
          </div>

          <div>
            <label className="block text-xs text-culpa-text-dim mb-1.5">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setEmailTouched(true)}
              className={cn(
                "w-full px-3 py-2.5 bg-culpa-bg border rounded-lg text-sm text-culpa-text placeholder:text-culpa-text-dim focus:outline-none focus:ring-2 transition-colors",
                emailTouched && email && !emailValid
                  ? "border-culpa-red/50 focus:ring-culpa-red/30 focus:border-culpa-red/50"
                  : "border-culpa-border focus:ring-culpa-red/30 focus:border-culpa-red/50"
              )}
              placeholder="you@example.com"
            />
            {emailTouched && email && !emailValid && (
              <p className="text-[11px] text-culpa-red mt-1">Please enter a valid email address</p>
            )}
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
              placeholder="Min. 8 characters"
            />
            {password && <PasswordChecklist password={password} />}
          </div>

          <div>
            <label className="block text-xs text-culpa-text-dim mb-1.5">Confirm password</label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={cn(
                "w-full px-3 py-2.5 bg-culpa-bg border rounded-lg text-sm text-culpa-text placeholder:text-culpa-text-dim focus:outline-none focus:ring-2 transition-colors",
                confirmPassword && password !== confirmPassword
                  ? "border-culpa-red/50 focus:ring-culpa-red/30"
                  : "border-culpa-border focus:ring-culpa-red/30 focus:border-culpa-red/50"
              )}
              placeholder="••••••••"
            />
            {confirmPassword && password !== confirmPassword && (
              <p className="text-[11px] text-culpa-red mt-1">Passwords do not match</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-culpa-red hover:bg-culpa-red/80 text-white font-medium text-sm
                       rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Creating account...' : 'Create account'}
          </button>

          <p className="text-center text-xs text-culpa-text-dim">
            Already have an account?{' '}
            <Link to="/login" className="text-culpa-red hover:text-culpa-red/80 transition-colors">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
