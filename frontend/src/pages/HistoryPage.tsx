import { useState, useMemo } from 'react'
import {
  History,
  Search,
  BarChart3,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Inbox,
} from 'lucide-react'
import { Button } from '../components/common'
import type { ScanHistoryItem, Grade } from '../types'
import './HistoryPage.css'

/* ── Grade helpers ───────────────────────────────────────── */

const GRADE_ORDER: Grade[] = ['A+', 'A', 'B', 'C', 'F']

const gradeToClass = (g: Grade): string => {
  switch (g) {
    case 'A+':
    case 'A':
      return 'a'
    case 'B':
      return 'b'
    case 'C':
      return 'c'
    case 'F':
      return 'f'
  }
}

/* ── Sort options ────────────────────────────────────────── */

type SortKey = 'date' | 'score' | 'findings' | 'grade'
type SortDir = 'asc' | 'desc'

const SORT_OPTIONS: { label: string; key: SortKey; dir: SortDir }[] = [
  { label: 'Newest First', key: 'date', dir: 'desc' },
  { label: 'Oldest First', key: 'date', dir: 'asc' },
  { label: 'Score ↑', key: 'score', dir: 'asc' },
  { label: 'Score ↓', key: 'score', dir: 'desc' },
  { label: 'Findings ↑', key: 'findings', dir: 'asc' },
  { label: 'Findings ↓', key: 'findings', dir: 'desc' },
]

/* ── Mock history data ───────────────────────────────────── */

function generateMockHistory(): ScanHistoryItem[] {
  const urls = [
    'https://example.com',
    'https://my-portfolio.dev',
    'https://api.internal.io',
    'https://staging.shop.vn',
    'https://blog.techstart.xyz',
    'https://dashboard.saas.app',
    'https://docs.openproject.org',
    'https://admin.crm-tool.com',
    'https://app.fintech.vn',
    'https://beta.healthcheck.io',
    'https://cdn.mediahost.net',
    'https://store.gadgets.co',
  ]

  const grades: Grade[] = ['A+', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'F', 'A', 'B', 'A+']
  const scores = [97, 88, 91, 74, 68, 72, 55, 48, 23, 85, 76, 95]
  const findingsCounts = [1, 3, 2, 5, 7, 6, 9, 11, 15, 4, 5, 0]
  const modes: ('quick' | 'full')[] = [
    'full', 'full', 'quick', 'full', 'full', 'quick',
    'full', 'full', 'full', 'quick', 'full', 'quick',
  ]

  const now = Date.now()
  return urls.map((url, i) => ({
    scan_id: `scan_${1000 + i}`,
    url,
    mode: modes[i],
    grade: grades[i],
    score: scores[i],
    findings_count: findingsCounts[i],
    started_at: new Date(now - (i * 3 + 1) * 3600 * 1000).toISOString(),
    duration_ms: 2000 + Math.floor(Math.random() * 6000),
  }))
}

const MOCK_HISTORY = generateMockHistory()

/* ── Props ───────────────────────────────────────────────── */

interface HistoryPageProps {
  /** History items (if undefined, uses mock data) */
  history?: ScanHistoryItem[]
  /** Called when user clicks a scan row to view results */
  onViewScan?: (scanId: string) => void
  /** Called when user clicks "New Scan" */
  onNewScan?: () => void
}

/* ── Component ───────────────────────────────────────────── */

export default function HistoryPage({
  history = MOCK_HISTORY,
  onViewScan,
  onNewScan,
}: HistoryPageProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [gradeFilter, setGradeFilter] = useState<Grade | 'all'>('all')
  const [sortIndex, setSortIndex] = useState(0) // default: Newest First

  // ── Derived stats ──────────────────────────────────────
  const stats = useMemo(() => {
    const total = history.length
    const avgScore =
      total > 0 ? Math.round(history.reduce((s, h) => s + h.score, 0) / total) : 0
    const bestGrade = history.reduce<Grade | null>((best, h) => {
      if (!best) return h.grade
      const order: Grade[] = ['A+', 'A', 'B', 'C', 'F']
      return order.indexOf(h.grade) < order.indexOf(best) ? h.grade : best
    }, null)
    const totalFindings = history.reduce((s, h) => s + h.findings_count, 0)
    return { total, avgScore, bestGrade, totalFindings }
  }, [history])

  // ── Filtered & sorted list ─────────────────────────────
  const filteredHistory = useMemo(() => {
    let items = [...history]

    // Text search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      items = items.filter((h) => h.url.toLowerCase().includes(q))
    }

    // Grade filter
    if (gradeFilter !== 'all') {
      items = items.filter((h) => h.grade === gradeFilter)
    }

    // Sort
    const { key, dir } = SORT_OPTIONS[sortIndex]
    items.sort((a, b) => {
      let cmp = 0
      switch (key) {
        case 'date':
          cmp = new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
          break
        case 'score':
          cmp = a.score - b.score
          break
        case 'findings':
          cmp = a.findings_count - b.findings_count
          break
        case 'grade': {
          const order: Grade[] = ['A+', 'A', 'B', 'C', 'F']
          cmp = order.indexOf(a.grade) - order.indexOf(b.grade)
          break
        }
      }
      return dir === 'asc' ? cmp : -cmp
    })

    return items
  }, [history, searchQuery, gradeFilter, sortIndex])

  // ── Formatters ─────────────────────────────────────────
  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (ms?: number) => {
    if (ms === undefined) return '—'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div className="history-page">
      {/* Page header */}
      <div className="history-page__header">
        <div>
          <h2 className="history-page__title">
            <History className="history-page__title-icon" size={24} />
            Scan History
          </h2>
          <p className="history-page__subtitle">
            Review and compare past security assessments
          </p>
        </div>
        {onNewScan && (
          <Button variant="primary" size="sm" onClick={onNewScan}>
            + New Scan
          </Button>
        )}
      </div>

      {/* Stats row */}
      <div className="history-stats">
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--scans">
            <BarChart3 size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{stats.total}</div>
            <div className="history-stat__label">Total Scans</div>
          </div>
        </div>
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--avg">
            <TrendingUp size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{stats.avgScore}</div>
            <div className="history-stat__label">Avg Score</div>
          </div>
        </div>
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--best">
            <ShieldCheck size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{stats.bestGrade ?? '—'}</div>
            <div className="history-stat__label">Best Grade</div>
          </div>
        </div>
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--issues">
            <AlertTriangle size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{stats.totalFindings}</div>
            <div className="history-stat__label">Total Findings</div>
          </div>
        </div>
      </div>

      {/* Toolbar: search + grade filter + sort */}
      <div className="history-toolbar">
        <div className="history-search">
          <Search className="history-search__icon" />
          <input
            className="history-search__input"
            type="text"
            placeholder="Search by URL..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            id="history-search-input"
          />
        </div>

        <div className="history-grade-filters">
          <button
            className={`history-grade-pill ${gradeFilter === 'all' ? 'history-grade-pill--active' : ''}`}
            onClick={() => setGradeFilter('all')}
          >
            All
          </button>
          {GRADE_ORDER.map((g) => (
            <button
              key={g}
              className={`history-grade-pill ${gradeFilter === g ? 'history-grade-pill--active' : ''}`}
              onClick={() => setGradeFilter(g)}
            >
              {g}
            </button>
          ))}
        </div>

        <select
          className="history-sort"
          value={sortIndex}
          onChange={(e) => setSortIndex(Number(e.target.value))}
          id="history-sort-select"
        >
          {SORT_OPTIONS.map((opt, i) => (
            <option key={i} value={i}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Data table */}
      {filteredHistory.length > 0 ? (
        <div className="history-table-wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th>Grade</th>
                <th>URL</th>
                <th className="history-table__col-score">Score</th>
                <th className="history-table__col-findings">Findings</th>
                <th className="history-table__col-mode">Mode</th>
                <th className="history-table__col-duration">
                  <Clock size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                  Duration
                </th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.map((item) => (
                <tr
                  key={item.scan_id}
                  onClick={() => onViewScan?.(item.scan_id)}
                  id={`history-row-${item.scan_id}`}
                >
                  <td>
                    <span
                      className={`history-table__grade history-table__grade--${gradeToClass(item.grade)}`}
                    >
                      {item.grade}
                    </span>
                  </td>
                  <td className="history-table__url" title={item.url}>
                    {item.url}
                  </td>
                  <td className="history-table__col-score">
                    <span className="history-table__score">{item.score}</span>
                    <span style={{ color: 'var(--text-disabled)', fontSize: 'var(--text-xs)' }}>
                      /100
                    </span>
                  </td>
                  <td className="history-table__col-findings">
                    <span
                      className={`history-table__findings ${
                        item.findings_count === 0
                          ? 'history-table__findings--zero'
                          : 'history-table__findings--has-issues'
                      }`}
                    >
                      {item.findings_count === 0 ? '✓ Clean' : `${item.findings_count} issues`}
                    </span>
                  </td>
                  <td className="history-table__col-mode">
                    <span className="history-table__mode">{item.mode}</span>
                  </td>
                  <td className="history-table__col-duration">
                    <span className="history-table__duration">
                      {formatDuration(item.duration_ms)}
                    </span>
                  </td>
                  <td>
                    <div className="history-table__date">
                      {formatDate(item.started_at)}
                    </div>
                    <div className="history-table__date" style={{ opacity: 0.6 }}>
                      {formatTime(item.started_at)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="history-empty">
          <Inbox className="history-empty__icon" />
          <div className="history-empty__title">
            {searchQuery || gradeFilter !== 'all'
              ? 'No matching scans'
              : 'No scans yet'}
          </div>
          <div className="history-empty__text">
            {searchQuery || gradeFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Run your first security scan to see results here'}
          </div>
        </div>
      )}
    </div>
  )
}
