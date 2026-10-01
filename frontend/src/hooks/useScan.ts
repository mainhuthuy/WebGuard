/* ============================================================
   useScan — Scan lifecycle orchestration hook
   Manages the full scan flow: start → progress → complete/error.
   Consumes useSSE internally and exposes a clean API surface
   for components to drive scan operations.
   ============================================================ */

import { useState, useCallback, useRef } from 'react'
import { buildMockScanResult } from '../utils/mockScan'
import { scanApi, toApiError, mapFinding, summarize, toGrade, toModuleName } from '../services'
import { USE_MOCK } from '../config'
import { useSSE } from './useSSE'
import type { SSEEvent } from './useSSE'
import type {
  ScanMode,
  ScanResult,
  ModuleName,
  Grade,
  ApiFinding,
  ApiScoring,
} from '../types'

/* ── Internal types ───────────────────────────────────────── */

/** Module step for progress display (exposed to consumers) */
export interface ModuleStep {
  id: ModuleName
  label: string
  status: 'pending' | 'active' | 'completed' | 'error'
  message?: string
  findingsCount: number
}

/** Log entry from the scan stream */
export interface LogEntry {
  time: string
  event: SSEEvent['event']
  message: string
}

/** Phase the scan UI is currently in */
export type ScanPhase = 'idle' | 'scanning' | 'completed' | 'errored'

/* ── Module metadata ──────────────────────────────────────── */

const MODULE_META: { id: ModuleName; label: string }[] = [
  { id: 'headers', label: 'Security Headers' },
  { id: 'cookies', label: 'Cookie Flags' },
  { id: 'ssl_tls', label: 'SSL / TLS Certificate' },
  { id: 'information', label: 'Information Disclosure' },
  { id: 'cors', label: 'CORS Configuration' },
]

/** Build initial module step list based on scan mode */
export function buildModuleSteps(mode: ScanMode): ModuleStep[] {
  const activeIds: ModuleName[] =
    mode === 'quick'
      ? ['headers', 'ssl_tls']
      : ['headers', 'cookies', 'ssl_tls', 'information', 'cors']

  return MODULE_META.filter((m) => activeIds.includes(m.id)).map((m) => ({
    id: m.id,
    label: m.label,
    status: 'pending' as const,
    findingsCount: 0,
  }))
}


/* ── Hook options ─────────────────────────────────────────── */

export interface UseScanOptions {
  /**
   * Use mock SSE simulation instead of real backend.
   * @default USE_MOCK (VITE_USE_MOCK env)
   */
  useMock?: boolean
}

/* ── Hook return type ─────────────────────────────────────── */

export interface UseScanReturn {
  /** Current scan phase */
  phase: ScanPhase
  /** Whether a scan is currently in progress */
  scanning: boolean
  /** Target URL being scanned */
  scanUrl: string
  /** Current overall progress (0-100) */
  progress: number
  /** Module step states for progress display */
  modules: ModuleStep[]
  /** Live log entries */
  logs: LogEntry[]
  /** Whether scan completed (either success or error) */
  completed: boolean
  /** Whether scan ended with an error */
  errored: boolean
  /** Completed scan result (null until scan finishes successfully) */
  result: ScanResult | null
  /** Human-readable error when the scan failed to start or errored */
  errorMessage: string | null
  /** Start a new scan */
  startScan: (url: string, mode: ScanMode) => void
  /** Cancel the running scan */
  cancelScan: () => void
  /** Reset all state back to idle */
  reset: () => void
}

/* ── useScan hook ─────────────────────────────────────────── */

export function useScan(options: UseScanOptions = {}): UseScanReturn {
  const { useMock = USE_MOCK } = options

  // Core state
  const [phase, setPhase] = useState<ScanPhase>('idle')
  const [scanUrl, setScanUrl] = useState('')
  const [progress, setProgress] = useState(0)
  const [modules, setModules] = useState<ModuleStep[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [result, setResult] = useState<ScanResult | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Refs for values needed inside SSE callbacks (avoid stale closures)
  const scanMetaRef = useRef<{
    url: string
    mode: ScanMode
    startTime: string
  }>({ url: '', mode: 'full', startTime: '' })
  const latestModulesRef = useRef<ModuleStep[]>([])
  /** Id of the backend scan currently streaming (real mode) */
  const activeScanIdRef = useRef<string | null>(null)
  /** Bumped on every start/cancel/reset so late async work can be ignored */
  const runIdRef = useRef(0)

  /** Handle each SSE event and update state accordingly */
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    const now = new Date().toISOString()

    // Update progress
    setProgress(event.progress)

    // Append to log
    setLogs((prev) => [
      ...prev,
      { time: now, event: event.event, message: event.message },
    ])

    // Module state transitions
    const moduleId = event.module ? toModuleName(event.module) : null

    if (event.event === 'module_start' && moduleId) {
      setModules((prev) => {
        const next = prev.map((m) =>
          m.id === moduleId
            ? { ...m, status: 'active' as const, message: 'Analyzing...' }
            : m
        )
        latestModulesRef.current = next
        return next
      })
    }

    if (event.event === 'module_completed' && moduleId) {
      setModules((prev) => {
        const next = prev.map((m) =>
          m.id === moduleId
            ? {
                ...m,
                status: 'completed' as const,
                message: event.message,
                findingsCount: event.findings_count ?? event.findings?.length ?? 0,
              }
            : m
        )
        latestModulesRef.current = next
        return next
      })
    }

    // Scan completed successfully
    if (event.event === 'complete') {
      const meta = scanMetaRef.current
      const apiFindings = event.findings as ApiFinding[] | null | undefined
      const scoring = event.data?.scoring as ApiScoring | undefined

      if (apiFindings && scoring) {
        // Real backend payload: findings + scoring come with the event
        const findings = apiFindings.map(mapFinding)
        const completedAt = new Date().toISOString()
        setResult({
          scan_id: event.scan_id,
          url: meta.url,
          mode: meta.mode,
          status: 'completed',
          grade: toGrade(scoring.grade),
          score: scoring.score,
          findings,
          summary: summarize(findings),
          started_at: meta.startTime,
          completed_at: completedAt,
          duration_ms: new Date(completedAt).getTime() - new Date(meta.startTime).getTime(),
        })
      } else {
        // Mock payload: synthesise findings from module counts
        const grade = (event.data?.grade as Grade) ?? 'B'
        const score = (event.data?.score as number) ?? 72
        setResult(
          buildMockScanResult(
            event.scan_id,
            meta.url,
            meta.mode,
            latestModulesRef.current,
            grade,
            score,
            meta.startTime,
          ),
        )
      }
      setPhase('completed')
    }

    // Scan errored
    if (event.event === 'error') {
      setErrorMessage(event.message)
      setPhase('errored')
    }
  }, [])

  // Wire up SSE
  const { connect, disconnect, statusRef } = useSSE({
    onEvent: handleSSEEvent,
    // Connection dropped before a terminal event (complete/error resets status to 'closed')
    onError: () => {
      if (statusRef.current === 'error') {
        setErrorMessage('Lost connection to the scan stream.')
        setPhase('errored')
      }
    },
    useMock,
  })

  /** Start a new scan */
  const startScan = useCallback(
    (url: string, mode: ScanMode) => {
      const runId = ++runIdRef.current
      const startTime = new Date().toISOString()

      setScanUrl(url)
      setPhase('scanning')
      setProgress(0)
      setLogs([])
      setResult(null)
      setErrorMessage(null)
      activeScanIdRef.current = null

      // The backend always runs every module, so quick mode only applies to the mock
      const initialModules = buildModuleSteps(useMock ? mode : 'full')
      setModules(initialModules)
      latestModulesRef.current = initialModules

      scanMetaRef.current = { url, mode, startTime }

      if (useMock) {
        // Mock mode: the "stream URL" is just the target URL for display
        connect(url, `scan_${Date.now()}`, mode)
        return
      }

      // Real mode: create the scan first, then open its SSE stream
      scanApi
        .createScan(url)
        .then((scan) => {
          if (runId !== runIdRef.current) return // cancelled / superseded meanwhile
          activeScanIdRef.current = scan.scan_id
          connect(scanApi.streamUrl(scan.scan_id), scan.scan_id, mode)
        })
        .catch((err) => {
          if (runId !== runIdRef.current) return
          const message = toApiError(err).message
          setLogs([{ time: new Date().toISOString(), event: 'error', message }])
          setErrorMessage(message)
          setPhase('errored')
        })
    },
    [connect, useMock],
  )

  /** Cancel the running scan */
  const cancelScan = useCallback(() => {
    runIdRef.current++
    disconnect()
    const scanId = activeScanIdRef.current
    activeScanIdRef.current = null
    if (!useMock && scanId) {
      // Best effort: the scan may already have finished on the server
      scanApi.cancelScan(scanId).catch(() => undefined)
    }
    setPhase('idle')
  }, [disconnect, useMock])

  /** Reset all state back to idle */
  const reset = useCallback(() => {
    runIdRef.current++
    disconnect()
    activeScanIdRef.current = null
    setPhase('idle')
    setScanUrl('')
    setProgress(0)
    setModules([])
    setLogs([])
    setResult(null)
    setErrorMessage(null)
  }, [disconnect])

  // Derived boolean states for convenience
  const scanning = phase === 'scanning'
  const completed = phase === 'completed' || phase === 'errored'
  const errored = phase === 'errored'

  return {
    phase,
    scanning,
    scanUrl,
    progress,
    modules,
    logs,
    completed,
    errored,
    result,
    errorMessage,
    startScan,
    cancelScan,
    reset,
  }
}
