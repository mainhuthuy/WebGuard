import './ProgressBar.css'

type ProgressColor = 'primary' | 'cyan' | 'emerald' | 'danger'
type ProgressSize = 'sm' | 'md' | 'lg'

interface ProgressBarProps {
  /** Current value (0-100) */
  value?: number
  /** Maximum value */
  max?: number
  /** Label text shown above the bar */
  label?: string
  /** Show percentage text */
  showValue?: boolean
  /** Bar color */
  color?: ProgressColor
  /** Track height */
  size?: ProgressSize
  /** Enable shimmer animation on the fill */
  animated?: boolean
  /** Indeterminate mode (unknown progress) */
  indeterminate?: boolean
  className?: string
}

export default function ProgressBar({
  value = 0,
  max = 100,
  label,
  showValue = true,
  color = 'primary',
  size = 'md',
  animated = false,
  indeterminate = false,
  className = '',
}: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))

  const fillClass = [
    'progress__fill',
    `progress__fill--${color}`,
    animated && 'progress__fill--animated',
    indeterminate && 'progress__fill--indeterminate',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={`progress ${className}`}>
      {(label || showValue) && (
        <div className="progress__label-row">
          {label && <span className="progress__label">{label}</span>}
          {showValue && !indeterminate && (
            <span className="progress__value">{Math.round(percentage)}%</span>
          )}
        </div>
      )}
      <div
        className={`progress__track progress__track--${size}`}
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : percentage}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={fillClass}
          style={indeterminate ? undefined : { width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

/* ── Steps sub-component for scan progress ───────────────── */

interface ProgressStepsProps {
  /** Total number of steps */
  total: number
  /** Number of completed steps */
  completed: number
  /** Index of currently active step (0-based) */
  activeIndex?: number
  className?: string
}

export function ProgressSteps({
  total,
  completed,
  activeIndex,
  className = '',
}: ProgressStepsProps) {
  return (
    <div className={`progress__steps ${className}`}>
      {Array.from({ length: total }, (_, i) => {
        const stepClass = [
          'progress__step',
          i < completed && 'progress__step--completed',
          i === activeIndex && 'progress__step--active',
        ]
          .filter(Boolean)
          .join(' ')
        return <div key={i} className={stepClass} />
      })}
    </div>
  )
}
