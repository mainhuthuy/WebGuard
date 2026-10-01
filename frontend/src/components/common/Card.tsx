import type { HTMLAttributes, ReactNode } from 'react'
import './Card.css'

type CardVariant = 'default' | 'interactive' | 'flat' | 'glow' | 'glass'
type CardPadding = 'compact' | 'default' | 'spacious'
type CardAccent = 'none' | 'primary' | 'cyan'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
  padding?: CardPadding
  accent?: CardAccent
  header?: ReactNode
  footer?: ReactNode
}

export default function Card({
  variant = 'default',
  padding = 'default',
  accent = 'none',
  header,
  footer,
  className = '',
  children,
  ...rest
}: CardProps) {
  const classes = [
    'wg-card',
    variant !== 'default' && `wg-card--${variant}`,
    padding !== 'default' && `wg-card--${padding}`,
    accent === 'primary' && 'wg-card--accent-top',
    accent === 'cyan' && 'wg-card--accent-cyan',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={classes} {...rest}>
      {header && <div className="wg-card__header">{header}</div>}
      <div className="wg-card__body">{children}</div>
      {footer && <div className="wg-card__footer">{footer}</div>}
    </div>
  )
}
