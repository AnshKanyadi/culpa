import React from 'react'
import { Link } from 'react-router-dom'
import { cn } from '../lib/utils'

type LogoSize = 'sm' | 'md' | 'lg' | 'xl'

const ICON_SIZES: Record<LogoSize, string> = {
  sm: 'h-6 w-6',
  md: 'h-7 w-7',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
}

const TEXT_SIZES: Record<LogoSize, string> = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
  xl: 'text-2xl',
}

interface LogoProps {
  size?: LogoSize
  showText?: boolean
  linkTo?: string
  className?: string
}

export function Logo({ size = 'md', showText = true, linkTo, className }: LogoProps) {
  const content = (
    <div className={cn('flex items-center gap-2', className)}>
      <img
        src="/culpa-logo.svg"
        alt="Culpa"
        className={cn(ICON_SIZES[size])}
      />
      {showText && (
        <span className={cn('font-mono font-bold text-culpa-text tracking-tight', TEXT_SIZES[size])}>
          culpa
        </span>
      )}
    </div>
  )

  if (linkTo) {
    return (
      <Link to={linkTo} className="hover:opacity-80 transition-opacity">
        {content}
      </Link>
    )
  }

  return content
}
