import { useEffect, useState } from 'react'
import { Clock, Globe } from 'lucide-react'
import type { Grade } from '../../types'
import './ScoreCard.css'

interface ScoreCardProps {
  grade: Grade
  score: number
  url: string
  duration?: number // ms
}

/** Map grade → CSS modifier */
const gradeClass: Record<Grade, string> = {
  'A+': 'score-card--a-plus',
  A: 'score-card--a',
  B: 'score-card--b',
  C: 'score-card--c',
  F: 'score-card--f',
}

/** Map grade → SVG stroke color */
const gradeStroke: Record<Grade, string> = {
  'A+': 'var(--grade-a-plus)',
  A: 'var(--grade-a)',
  B: 'var(--grade-b)',
  C: 'var(--grade-c)',
  F: 'var(--grade-f)',
}

export default function ScoreCard({ grade, score, url, duration }: ScoreCardProps) {
  const [animatedOffset, setAnimatedOffset] = useState(339.292)

  // SVG circle math
  const radius = 54
  const circumference = 2 * Math.PI * radius // ≈ 339.292
  const fillPercent = Math.min(100, Math.max(0, score)) / 100
  const targetOffset = circumference * (1 - fillPercent)

  // Animate on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      setAnimatedOffset(targetOffset)
    }, 100)
    return () => clearTimeout(timer)
  }, [targetOffset])

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div className={`score-card ${gradeClass[grade]}`}>
      {/* Circular ring */}
      <div className="score-card__ring">
        <svg className="score-card__svg" viewBox="0 0 120 120">
          <circle
            className="score-card__track"
            cx="60"
            cy="60"
            r={radius}
          />
          <circle
            className="score-card__fill"
            cx="60"
            cy="60"
            r={radius}
            stroke={gradeStroke[grade]}
            strokeDasharray={circumference}
            strokeDashoffset={animatedOffset}
          />
        </svg>
        <div className="score-card__grade">
          <span className="score-card__letter">{grade}</span>
          <span className="score-card__sublabel">Security Grade</span>
        </div>
      </div>

      {/* Score number */}
      <div className="score-card__score">
        {score}<span className="score-card__score-max"> / 100</span>
      </div>

      {/* Meta info */}
      <div className="score-card__meta">
        <span className="score-card__meta-item">
          <Globe className="score-card__meta-icon" />
          {url}
        </span>
        {duration !== undefined && (
          <span className="score-card__meta-item">
            <Clock className="score-card__meta-icon" />
            {formatDuration(duration)}
          </span>
        )}
      </div>
    </div>
  )
}
