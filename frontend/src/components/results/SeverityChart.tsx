import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { Severity } from '../../types'
import './SeverityChart.css'

interface SeveritySummary {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

interface SeverityChartProps {
  summary: SeveritySummary
  /** Show donut chart (true) or just bar + legend (false) */
  showChart?: boolean
}

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

const SEVERITY_COLORS: Record<Severity, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#64748b',
}

const SEVERITY_LABELS: Record<Severity, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Informational',
}

/** Custom dark tooltip */
function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) {
  if (!active || !payload?.length) return null
  const item = payload[0]
  return (
    <div className="severity-tooltip">
      <div className="severity-tooltip__label">{item.name}</div>
      <div className="severity-tooltip__value">
        {item.value} finding{item.value !== 1 ? 's' : ''}
      </div>
    </div>
  )
}

export default function SeverityChart({ summary, showChart = true }: SeverityChartProps) {
  // Sum only the known severities: callers pass ScanResult.summary, which also has a `total`
  // field that must not be counted again.
  const total = SEVERITY_ORDER.reduce((sum, s) => sum + summary[s], 0)

  // Prepare chart data (only non-zero slices)
  const chartData = SEVERITY_ORDER
    .filter((s) => summary[s] > 0)
    .map((s) => ({
      name: SEVERITY_LABELS[s],
      value: summary[s],
      severity: s,
    }))

  return (
    <div className="severity-chart">
      {/* Donut chart */}
      {showChart && chartData.length > 0 && (
        <div className="severity-chart__chart-wrapper">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                animationBegin={200}
                animationDuration={800}
              >
                {chartData.map((entry) => (
                  <Cell
                    key={entry.severity}
                    fill={SEVERITY_COLORS[entry.severity]}
                    stroke="transparent"
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Horizontal severity bar */}
      {total > 0 && (
        <div className="severity-bar">
          {SEVERITY_ORDER.map((s) => {
            const count = summary[s]
            if (count === 0) return null
            return (
              <div
                key={s}
                className={`severity-bar__segment severity-bar__segment--${s}`}
                style={{ width: `${(count / total) * 100}%` }}
                title={`${SEVERITY_LABELS[s]}: ${count}`}
              />
            )
          })}
        </div>
      )}

      {/* Legend */}
      <div className="severity-chart__legend">
        {SEVERITY_ORDER.map((s) => (
          <div key={s} className="severity-legend__item">
            <span className={`severity-legend__dot severity-legend__dot--${s}`} />
            <span className="severity-legend__label">{SEVERITY_LABELS[s]}</span>
            <span className="severity-legend__count">{summary[s]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
