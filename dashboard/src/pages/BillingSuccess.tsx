import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'

export function BillingSuccess() {
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => navigate('/'), 3000)
    return () => clearTimeout(timer)
  }, [navigate])

  return (
    <div className="min-h-screen bg-culpa-bg flex items-center justify-center px-4">
      <div className="text-center">
        <div className="w-16 h-16 bg-culpa-green/15 border border-culpa-green/30 rounded-full
                        flex items-center justify-center mx-auto mb-6">
          <Check size={28} className="text-culpa-green" />
        </div>
        <h1 className="text-xl font-bold text-culpa-text mb-2">Welcome to Pro!</h1>
        <p className="text-sm text-culpa-text-dim mb-6">
          Unlimited sessions, 90-day retention, and team sharing are now active.
        </p>
        <p className="text-xs text-culpa-text-dim">Redirecting to dashboard...</p>
      </div>
    </div>
  )
}
