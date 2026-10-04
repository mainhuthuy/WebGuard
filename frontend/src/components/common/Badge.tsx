import type { HTMLAttributes, ReactNode } from 'react'
import './Badge.css'

type BadgeVariant =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'info'
  | 'success'
  | 'primary'
  | 'neutral'

type BadgeSize = 'sm' | 'md' | 'lg'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  size?: BadgeSize
  /** Show a small dot indicator before the label */
  dot?: boolean
  /** Pulse the dot (for live/active states) */
  pulse?: boolean
  /** Icon element to show before the label */
  icon?: ReactNode
}

export default function Badge({
  variant = 'neutral',
  size = 'md',
  dot = false,
  pulse = false,
  icon,
  className = '',
  children,
  ...rest
}: BadgeProps) {
  const classes = [
    'badge',
    `badge--${variant}`,
    `badge--${size}`,
    pulse && 'badge--pulse',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span className={classes} {...rest}>
      {dot && <span className="badge__dot" />}
      {icon && <span className="badge__icon">{icon}</span>}
      {children}
    </span>
  )
}
