import { useEffect, useRef } from 'react'
import { CheckCircle2, AlertCircle, Circle } from 'lucide-react'
import { ProgressBar } from '../common'
import type { ModuleName } from '../../types'
import './ScanProgress.css'

/* ── Types matching backend ScanStreamEvent ───────────────── */

export type ScanEventType =
  | 'start'
  | 'module_start'
  | 'module_completed'
  | 'scoring'
  | 'complete'
  | 'error'

export interface ScanStreamEvent {
  event: ScanEventType
  scan_id: string
  progress: number
  message: string
  module?: string | null
  findings_count?: number
  data?: Record<string, unknown> | null
}

type ModuleStatus = 'pending' | 'active' | 'completed' | 'error'

interface ModuleStep {
  id: ModuleName
  label: string
  status: ModuleStatus
  message?: string
  findingsCount: number
}

interface LogEntry {
  time: string
  event: ScanEventType
  message: string
}

/* ── Module metadata ─────────────────────────────────────── */

const MODULE_META: { id: ModuleName; label: string }[] = [
  { id: 'headers', label: 'Security Headers' },
  { id: 'cookies', label: 'Cookie Flags' },
  { id: 'ssl_tls', label: 'SSL / TLS Certificate' },
  { id: 'information', label: 'Information Disclosure' },
  { id: 'cors', label: 'CORS Configuration' },
]

/* ── Props ────────────────────────────────────────────────── */

interface ScanProgressProps {
  /** Target URL being scanned */
  url: string
  /** Current overall progress (0-100) */
  progress: number
  /** Module step states */
  modules: ModuleStep[]
  /** Live log entries */
  logs: LogEntry[]
  /** Whether scan is fully completed */
  completed: boolean
  /** Whether scan errored */
  errored?: boolean
  /** Called when user clicks "View Results" after completion */
  onViewResults?: () => void
  /** Called when user clicks "Cancel" */
  onCancel?: () => void
}

export default function ScanProgress({
  url,
  progress,
  modules,
  logs,
  completed,
  errored = false,
  onViewResults,
  onCancel,
}: ScanProgressProps) {
  const logEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll log to bottom
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="scan-progress">
      {/* Header */}
      <div className="scan-progress__header">
        <h2 className="scan-progress__title">
          {completed
            ? errored
              ? 'Scan Failed'
              : 'Scan Complete'
            : 'Scanning Target...'}
        </h2>
        <span className="scan-progress__url">{url}</span>
      </div>

      {/* Progress bar */}
      <div className="scan-progress__bar">
        <ProgressBar
          value={progress}
          color={errored ? 'danger' : completed ? 'emerald' : 'cyan'}
          size="md"
          animated={!completed}
          label={completed ? 'Completed' : 'Scan Progress'}
        />
      </div>

      {/* Module steps */}
      <div className="scan-progress__modules">
        {modules.map((mod) => (
          <div
            key={mod.id}
            className={`scan-module scan-module--${mod.status}`}
          >
            {/* Status icon */}
            <div className={`scan-module__icon scan-module__icon--${mod.status}`}>
              {mod.status === 'pending' && <Circle size={16} />}
              {mod.status === 'active' && <div className="scan-module__spinner" />}
              {mod.status === 'completed' && <CheckCircle2 size={16} />}
              {mod.status === 'error' && <AlertCircle size={16} />}
            </div>

            {/* Name + message */}
            <div className="scan-module__info">
              <div className="scan-module__name">{mod.label}</div>
              {mod.message && (
                <div className="scan-module__message">{mod.message}</div>
              )}
            </div>

            {/* Findings count */}
            {mod.status === 'completed' && (
              <div
                className={`scan-module__findings ${
                  mod.findingsCount > 0 ? 'scan-module__findings--has-issues' : ''
                }`}
              >
                {mod.findingsCount > 0
                  ? `${mod.findingsCount} issue${mod.findingsCount > 1 ? 's' : ''}`
                  : '✓ Pass'}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Live log feed */}
      {logs.length > 0 && (
        <div className="scan-progress__log">
          {logs.map((log, i) => (
            <div key={i} className="scan-log__entry">
              <span className="scan-log__time">{formatTime(log.time)}</span>
              <span className={`scan-log__event scan-log__event--${log.event}`}>
                [{log.event}]
              </span>
              <span className="scan-log__msg">{log.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      )}

      {/* Completed actions */}
      {completed && !errored && (
        <div className="scan-progress__done">
          <CheckCircle2 className="scan-progress__done-icon" />
          <div className="scan-progress__done-text">
            Security assessment completed successfully
          </div>
          {onViewResults && (
            <button
              className="btn btn--primary btn--lg"
              onClick={onViewResults}
              id="view-results-btn"
            >
              View Results
            </button>
          )}
        </div>
      )}

      {/* Cancel button while running */}
      {!completed && onCancel && (
        <div style={{ textAlign: 'center', marginTop: 'var(--space-4)' }}>
          <button
            className="btn btn--ghost btn--sm"
            onClick={onCancel}
          >
            Cancel Scan
          </button>
        </div>
      )}
    </div>
  )
}

/* ── Helper: build initial modules state from mode ────────── */

export function buildInitialModules(
  mode: 'quick' | 'full'
): ModuleStep[] {
  const activeIds: ModuleName[] =
    mode === 'quick'
      ? ['headers', 'ssl_tls']
      : ['headers', 'cookies', 'ssl_tls', 'information', 'cors']

  return MODULE_META.filter((m) => activeIds.includes(m.id)).map((m) => ({
    id: m.id,
    label: m.label,
    status: 'pending' as ModuleStatus,
    findingsCount: 0,
  }))
}
