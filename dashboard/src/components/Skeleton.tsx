import React from 'react'
import { cn } from '../lib/utils'

export function SkeletonPulse({ className }: { className?: string }) {
  return (
    <div className={cn('bg-culpa-muted animate-pulse rounded-lg', className)} />
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-culpa-surface border border-culpa-border rounded-xl p-4">
      <SkeletonPulse className="w-2/3 h-4 mb-3" />

      <div className="flex items-center gap-2 mb-3">
        <SkeletonPulse className="w-16 h-3" />
        <SkeletonPulse className="w-20 h-3" />
      </div>

      <div className="flex items-center gap-4">
        <SkeletonPulse className="w-14 h-3" />
        <SkeletonPulse className="w-16 h-3" />
        <SkeletonPulse className="w-12 h-3" />
        <SkeletonPulse className="w-14 h-3" />
      </div>

      <div className="mt-2">
        <SkeletonPulse className="w-24 h-5 rounded" />
      </div>
    </div>
  )
}

export function SkeletonTimeline() {
  return (
    <div className="px-4 py-4 space-y-4">
      {Array.from({ length: 7 }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <SkeletonPulse className="w-10 h-10 rounded-full flex-shrink-0" />
          <div className="flex-1 min-w-0 space-y-2 pt-1">
            <SkeletonPulse className="w-4/5 h-3.5" />
            <SkeletonPulse className="w-1/2 h-2.5" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function SkeletonDetail() {
  return (
    <div className="p-6 space-y-6">
      <div className="space-y-2">
        <SkeletonPulse className="w-1/3 h-5" />
        <SkeletonPulse className="w-1/2 h-3" />
      </div>

      <div className="bg-culpa-surface border border-culpa-border rounded-xl p-4 space-y-3">
        <SkeletonPulse className="w-1/4 h-3" />
        <SkeletonPulse className="w-full h-24" />
      </div>

      <div className="bg-culpa-surface border border-culpa-border rounded-xl p-4 space-y-3">
        <SkeletonPulse className="w-1/5 h-3" />
        <SkeletonPulse className="w-full h-16" />
      </div>

      <div className="bg-culpa-surface border border-culpa-border rounded-xl p-4 space-y-3">
        <SkeletonPulse className="w-1/6 h-3" />
        <SkeletonPulse className="w-3/4 h-10" />
      </div>
    </div>
  )
}

export function SkeletonOverview() {
  return (
    <div className="p-3 space-y-4">
      <div className="space-y-2">
        <SkeletonPulse className="w-16 h-2.5" />
        <SkeletonPulse className="w-24 h-4" />
      </div>

      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between">
            <SkeletonPulse className="w-20 h-3" />
            <SkeletonPulse className="w-12 h-3" />
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <SkeletonPulse className="w-16 h-2.5" />
        <SkeletonPulse className="w-32 h-5 rounded" />
      </div>

      <div className="space-y-2">
        <SkeletonPulse className="w-12 h-2.5" />
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonPulse key={i} className="w-full h-3" />
        ))}
      </div>
    </div>
  )
}
