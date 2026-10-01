/* ============================================================
   useScan — Scan lifecycle orchestration hook
   Manages the full scan flow: start → progress → complete/error.
   Consumes useSSE internally and exposes a clean API surface
   for components to drive scan operations.
   ============================================================ */

import { useState, useCallback, useRef } from 'react'
import { buildMockScanResult } from '../utils/mockScan'
import { useSSE } from './useSSE'
import type { SSEEvent } from './useSSE'
import type {
  ScanMode,
  ScanResult,
  ModuleName,
  Grade,
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
   * @default true
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
  /** Start a new scan */
  startScan: (url: string, mode: ScanMode) => void
  /** Cancel the running scan */
  cancelScan: () => void
  /** Reset all state back to idle */
  reset: () => void
}

/* ── useScan hook ─────────────────────────────────────────── */

export function useScan(options: UseScanOptions = {}): UseScanReturn {
  const { useMock = true } = options

  // Core state
  const [phase, setPhase] = useState<ScanPhase>('idle')
  const [scanUrl, setScanUrl] = useState('')
  const [progress, setProgress] = useState(0)
  const [modules, setModules] = useState<ModuleStep[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [result, setResult] = useState<ScanResult | null>(null)

  // Refs for values needed inside SSE callbacks (avoid stale closures)
  const scanMetaRef = useRef<{
    url: string
    mode: ScanMode
    startTime: string
  }>({ url: '', mode: 'full', startTime: '' })
  const latestModulesRef = useRef<ModuleStep[]>([])

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
    if (event.event === 'module_start' && event.module) {
      setModules((prev) => {
        const next = prev.map((m) =>
          m.id === event.module
            ? { ...m, status: 'active' as const, message: 'Analyzing...' }
            : m
        )
        latestModulesRef.current = next
        return next
      })
    }

    if (event.event === 'module_completed' && event.module) {
      setModules((prev) => {
        const next = prev.map((m) =>
          m.id === event.module
            ? {
                ...m,
                status: 'completed' as const,
                message: event.message,
                findingsCount: event.findings_count ?? 0,
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
      const grade = (event.data?.grade as Grade) ?? 'B'
      const score = (event.data?.score as number) ?? 72
      const scanResult = buildMockScanResult(
        event.scan_id,
        meta.url,
        meta.mode,
        latestModulesRef.current,
        grade,
        score,
        meta.startTime,
      )
      setResult(scanResult)
      setPhase('completed')
    }

    // Scan errored
    if (event.event === 'error') {
      setPhase('errored')
    }
  }, [])

  // Wire up SSE
  const { connect, disconnect } = useSSE({
    onEvent: handleSSEEvent,
    useMock,
  })

  /** Start a new scan */
  const startScan = useCallback(
    (url: string, mode: ScanMode) => {
      // Reset all state
      const startTime = new Date().toISOString()
      const scanId = `scan_${Date.now()}`

      setScanUrl(url)
      setPhase('scanning')
      setProgress(0)
      setLogs([])
      setResult(null)

      const initialModules = buildModuleSteps(mode)
      setModules(initialModules)
      latestModulesRef.current = initialModules

      // Save meta for result building
      scanMetaRef.current = { url, mode, startTime }

      // Connect to SSE stream
      // In mock mode, url is passed as the stream URL for display purposes
      // In real mode, this would be the actual API endpoint like `/api/v1/scan/{scanId}/stream`
      const streamUrl = useMock
        ? url
        : `/api/v1/scan/${scanId}/stream`

      connect(streamUrl, scanId, mode)
    },
    [connect, useMock],
  )

  /** Cancel the running scan */
  const cancelScan = useCallback(() => {
    disconnect()
    setPhase('idle')
  }, [disconnect])

  /** Reset all state back to idle */
  const reset = useCallback(() => {
    disconnect()
    setPhase('idle')
    setScanUrl('')
    setProgress(0)
    setModules([])
    setLogs([])
    setResult(null)
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
    startScan,
    cancelScan,
    reset,
  }
}
