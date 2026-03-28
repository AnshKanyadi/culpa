import React from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { ArrowLeft, Check, ExternalLink, Loader2 } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { cn } from '../lib/utils'

const FREE_FEATURES = [
  '3 cloud sessions',
  '7-day retention',
  '5 forks per session',
  'Local replay & fork',
  'Anthropic + OpenAI interceptors',
]

const PRO_FEATURES = [
  'Unlimited cloud sessions',
  '90-day retention',
  'Unlimited fork history',
  'Team sharing',
  'Priority support',
]

export function Billing() {
  const { user } = useAuth()

  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: () => api.auth.usage(),
  })

  const { data: billing } = useQuery({
    queryKey: ['billing-status'],
    queryFn: () => api.billing.status(),
  })

  const checkoutMutation = useMutation({
    mutationFn: () => api.billing.createCheckout(),
    onSuccess: (data) => {
      window.location.href = data.checkout_url
    },
  })

  const portalMutation = useMutation({
    mutationFn: () => api.billing.createPortal(),
    onSuccess: (data) => {
      window.location.href = data.portal_url
    },
  })

  const isPro = user?.plan === 'pro'

  return (
    <div className="min-h-screen bg-culpa-bg">
      <div className="border-b border-culpa-border bg-culpa-surface">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <Link to="/" className="text-culpa-text-dim hover:text-culpa-text transition-colors">
              <ArrowLeft size={16} />
            </Link>
            <div>
              <h1 className="text-sm font-semibold text-culpa-text">Billing</h1>
              <p className="text-xs text-culpa-text-dim">{user?.email}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-culpa-text-dim uppercase tracking-wider">Current plan</span>
            <span className={cn(
              'text-xs font-bold px-2 py-0.5 rounded',
              isPro ? 'bg-culpa-green/15 text-culpa-green border border-culpa-green/30' : 'bg-culpa-muted text-culpa-text-dim',
            )}>
              {isPro ? 'Pro' : 'Free'}
            </span>
          </div>

          {usage && (
            <div className="mt-3 text-xs text-culpa-text-dim">
              {usage.session_limit
                ? `${usage.session_count} / ${usage.session_limit} sessions used`
                : `${usage.session_count} sessions`
              }
              {' · '}
              {usage.retention_days}-day retention
            </div>
          )}

          {billing?.subscription && (
            <div className="mt-2 text-xs text-culpa-text-dim">
              Subscription: {billing.subscription.status}
              {billing.subscription.cancel_at_period_end && (
                <span className="text-culpa-orange ml-1">(cancels at period end)</span>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className={cn(
            'border rounded-2xl p-6',
            !isPro ? 'border-culpa-text-dim/30 bg-culpa-surface' : 'border-culpa-border bg-culpa-surface/50',
          )}>
            <h3 className="text-sm font-semibold text-culpa-text">Free</h3>
            <div className="mt-1 mb-4">
              <span className="text-2xl font-bold text-culpa-text">$0</span>
              <span className="text-xs text-culpa-text-dim ml-1">forever</span>
            </div>
            <ul className="space-y-2">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-xs text-culpa-text-dim">
                  <Check size={12} className="mt-0.5 text-culpa-text-dim shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            {!isPro && (
              <div className="mt-5 text-center text-xs text-culpa-text-dim">Current plan</div>
            )}
          </div>

          <div className={cn(
            'border rounded-2xl p-6 relative',
            isPro ? 'border-culpa-red/50 bg-culpa-surface' : 'border-culpa-red/30 bg-culpa-surface',
          )}>
            <h3 className="text-sm font-semibold text-culpa-text">Pro</h3>
            <div className="mt-1 mb-4">
              <span className="text-2xl font-bold text-culpa-text">$29</span>
              <span className="text-xs text-culpa-text-dim ml-1">/ month</span>
            </div>
            <ul className="space-y-2">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-xs text-culpa-text">
                  <Check size={12} className="mt-0.5 text-culpa-red shrink-0" />
                  {f}
                </li>
              ))}
            </ul>

            {!isPro && (
              <button
                onClick={() => checkoutMutation.mutate()}
                disabled={checkoutMutation.isPending}
                className="mt-5 w-full py-2.5 bg-culpa-red hover:bg-culpa-red/80 text-white font-medium text-sm
                           rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center justify-center gap-2"
              >
                {checkoutMutation.isPending ? (
                  <><Loader2 size={14} className="animate-spin" /> Redirecting...</>
                ) : (
                  'Upgrade to Pro'
                )}
              </button>
            )}
            {isPro && (
              <button
                onClick={() => portalMutation.mutate()}
                disabled={portalMutation.isPending}
                className="mt-5 w-full py-2.5 bg-culpa-muted hover:bg-culpa-border text-culpa-text font-medium text-sm
                           rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {portalMutation.isPending ? (
                  <><Loader2 size={14} className="animate-spin" /> Loading...</>
                ) : (
                  <>Manage subscription <ExternalLink size={12} /></>
                )}
              </button>
            )}
          </div>
        </div>

        {checkoutMutation.isError && (
          <div className="bg-culpa-red-dim border border-culpa-red/30 text-culpa-red text-sm px-4 py-3 rounded-lg">
            {checkoutMutation.error instanceof Error ? checkoutMutation.error.message : 'Failed to create checkout'}
          </div>
        )}
      </div>
    </div>
  )
}
