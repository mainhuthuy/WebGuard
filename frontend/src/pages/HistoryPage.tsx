import { useState } from 'react'
import {
  History,
  Search,
  BarChart3,
  TrendingUp,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Inbox,
  Trash2,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import { Button, Modal } from '../components/common'
import { useHistory, type HistorySort } from '../hooks/useHistory'
import { GRADE_ORDER } from '../utils/mockHistory'
import type { ScanHistoryItem, Grade, ScanStatus } from '../types'
import './HistoryPage.css'

/* ── Grade helpers ───────────────────────────────────────── */

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

const STATUS_LABEL: Record<ScanStatus, string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

/* ── Sort options ────────────────────────────────────────── */

const SORT_OPTIONS: { label: string; value: HistorySort }[] = [
  { label: 'Newest First', value: 'newest' },
  { label: 'Oldest First', value: 'oldest' },
  { label: 'Score ↓', value: 'score_desc' },
  { label: 'Score ↑', value: 'score_asc' },
]

/* ── Formatters ──────────────────────────────────────────── */

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })

const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })

const formatDuration = (ms?: number) => {
  if (ms === undefined) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/* ── Props ───────────────────────────────────────────────── */

interface HistoryPageProps {
  /** Called when the user opens a completed scan */
  onViewScan?: (item: ScanHistoryItem) => void
  /** Error from opening a scan (e.g. the detail request failed) */
  openError?: string | null
  /** Called when user clicks "New Scan" */
  onNewScan?: () => void
}

/* ── Component ───────────────────────────────────────────── */

export default function HistoryPage({ onViewScan, onNewScan, openError }: HistoryPageProps) {
  const h = useHistory()
  const [pendingDelete, setPendingDelete] = useState<ScanHistoryItem | null>(null)
  const [deleting, setDeleting] = useState(false)

  const filtering = h.search.trim() !== '' || h.grade !== 'all'

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    await h.deleteScan(pendingDelete.scan_id)
    setDeleting(false)
    setPendingDelete(null)
  }

  const openScan = (item: ScanHistoryItem) => {
    if (item.status === 'completed') onViewScan?.(item)
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
          <p className="history-page__subtitle">Review and compare past security assessments</p>
        </div>
        <div className="history-page__actions">
          <Button
            variant="ghost"
            size="sm"
            onClick={h.refresh}
            leftIcon={<RefreshCw size={14} />}
            id="history-refresh-btn"
          >
            Refresh
          </Button>
          {onNewScan && (
            <Button variant="primary" size="sm" onClick={onNewScan}>
              + New Scan
            </Button>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="history-stats">
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--scans">
            <BarChart3 size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{h.stats?.total ?? '—'}</div>
            <div className="history-stat__label">Total Scans</div>
          </div>
        </div>
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--avg">
            <TrendingUp size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{h.stats?.avgScore ?? '—'}</div>
            <div className="history-stat__label">Avg Score</div>
          </div>
        </div>
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--best">
            <ShieldCheck size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{h.stats?.bestGrade ?? '—'}</div>
            <div className="history-stat__label">Best Grade</div>
          </div>
        </div>
        <div className="history-stat">
          <div className="history-stat__icon-wrapper history-stat__icon-wrapper--issues">
            <CheckCircle2 size={20} />
          </div>
          <div className="history-stat__info">
            <div className="history-stat__value">{h.stats?.completed ?? '—'}</div>
            <div className="history-stat__label">Completed</div>
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
            value={h.search}
            onChange={(e) => h.setSearch(e.target.value)}
            id="history-search-input"
          />
        </div>

        <div className="history-grade-filters">
          <button
            className={`history-grade-pill ${h.grade === 'all' ? 'history-grade-pill--active' : ''}`}
            onClick={() => h.setGrade('all')}
          >
            All
          </button>
          {GRADE_ORDER.map((g) => (
            <button
              key={g}
              className={`history-grade-pill ${h.grade === g ? 'history-grade-pill--active' : ''}`}
              onClick={() => h.setGrade(g)}
            >
              {g}
            </button>
          ))}
        </div>

        <select
          className="history-sort"
          value={h.sort}
          onChange={(e) => h.setSort(e.target.value as HistorySort)}
          id="history-sort-select"
          aria-label="Sort scans"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error banner */}
      {(h.error || openError) && (
        <div className="history-error" role="alert">
          <AlertCircle size={16} />
          <span>{h.error ?? openError}</span>
        </div>
      )}

      {/* Data table */}
      {h.items.length > 0 ? (
        <div className={`history-table-wrapper ${h.loading ? 'history-table-wrapper--loading' : ''}`}>
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
                <th className="history-table__col-actions" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {h.items.map((item) => {
                const openable = item.status === 'completed'
                return (
                  <tr
                    key={item.scan_id}
                    className={openable ? '' : 'history-table__row--static'}
                    onClick={() => openScan(item)}
                    id={`history-row-${item.scan_id}`}
                  >
                    <td>
                      {item.grade ? (
                        <span
                          className={`history-table__grade history-table__grade--${gradeToClass(item.grade)}`}
                        >
                          {item.grade}
                        </span>
                      ) : (
                        <span className={`history-table__status history-table__status--${item.status}`}>
                          {STATUS_LABEL[item.status]}
                        </span>
                      )}
                    </td>
                    <td className="history-table__url" title={item.url}>
                      {item.url}
                    </td>
                    <td className="history-table__col-score">
                      {item.score === null ? (
                        '—'
                      ) : (
                        <>
                          <span className="history-table__score">{item.score}</span>
                          <span style={{ color: 'var(--text-disabled)', fontSize: 'var(--text-xs)' }}>
                            /100
                          </span>
                        </>
                      )}
                    </td>
                    <td className="history-table__col-findings">
                      {openable ? (
                        <span
                          className={`history-table__findings ${
                            item.findings_count === 0
                              ? 'history-table__findings--zero'
                              : 'history-table__findings--has-issues'
                          }`}
                        >
                          {item.findings_count === 0 ? '✓ Clean' : `${item.findings_count} issues`}
                        </span>
                      ) : (
                        '—'
                      )}
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
                      <div className="history-table__date">{formatDate(item.started_at)}</div>
                      <div className="history-table__date" style={{ opacity: 0.6 }}>
                        {formatTime(item.started_at)}
                      </div>
                    </td>
                    <td className="history-table__col-actions">
                      <button
                        className="history-table__delete"
                        title="Delete scan"
                        aria-label={`Delete scan of ${item.url}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          setPendingDelete(item)
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : h.loading ? (
        <div className="history-empty" role="status">
          <div className="history-empty__title">Loading scans…</div>
        </div>
      ) : (
        !h.error && (
          <div className="history-empty">
            <Inbox className="history-empty__icon" />
            <div className="history-empty__title">
              {filtering ? 'No matching scans' : 'No scans yet'}
            </div>
            <div className="history-empty__text">
              {filtering
                ? 'Try adjusting your search or filters'
                : 'Run your first security scan to see results here'}
            </div>
          </div>
        )
      )}

      {/* Pagination */}
      {h.totalPages > 1 && (
        <nav className="history-pagination" aria-label="Pagination">
          <Button
            variant="ghost"
            size="sm"
            disabled={h.page <= 1}
            onClick={() => h.setPage(h.page - 1)}
            leftIcon={<ChevronLeft size={14} />}
          >
            Previous
          </Button>
          <span className="history-pagination__info">
            Page {h.page} of {h.totalPages} · {h.total} scans
          </span>
          <Button
            variant="ghost"
            size="sm"
            disabled={h.page >= h.totalPages}
            onClick={() => h.setPage(h.page + 1)}
            rightIcon={<ChevronRight size={14} />}
          >
            Next
          </Button>
        </nav>
      )}

      {/* Delete confirmation */}
      <Modal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title="Delete scan?"
        size="sm"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button variant="danger" size="sm" loading={deleting} onClick={confirmDelete}>
              Delete
            </Button>
          </>
        }
      >
        <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
          This permanently removes the scan of <strong>{pendingDelete?.url}</strong> and all of its
          findings.
        </p>
      </Modal>
    </div>
  )
}
