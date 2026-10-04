/* ============================================================
   useSSE — Server-Sent Events connection hook
   Manages EventSource lifecycle: connect, parse, reconnect, close.
   Falls back to mock simulation when backend is unavailable.
   ============================================================ */

import { useRef, useCallback, useEffect } from 'react'
import { USE_MOCK } from '../config'
import type { ScanMode, ModuleName } from '../types'

/* ── SSE Event types (mirrors backend ScanStreamEvent) ────── */

export type SSEEventType =
  | 'start'
  | 'module_start'
  | 'module_completed'
  | 'scoring'
  | 'complete'
  | 'error'

export interface SSEEvent {
  event: SSEEventType
  scan_id: string
  progress: number
  message: string
  module?: string | null
  findings_count?: number
  findings?: unknown[] | null
  data?: Record<string, unknown> | null
}

/** Connection states for the SSE stream */
export type SSEStatus = 'idle' | 'connecting' | 'connected' | 'closed' | 'error'

/* ── Hook options ─────────────────────────────────────────── */

export interface UseSSEOptions {
  /** Called for every parsed SSE event */
  onEvent: (event: SSEEvent) => void
  /** Called when the connection is established */
  onOpen?: () => void
  /** Called when the connection is closed (intentionally or by server) */
  onClose?: () => void
  /** Called on connection error */
  onError?: (error: Event | Error) => void
  /**
   * Use mock SSE simulation instead of real EventSource.
   * Useful during development or when backend is unavailable.
   * @default USE_MOCK (VITE_USE_MOCK env)
   */
  useMock?: boolean
}

/* ── Hook return type ─────────────────────────────────────── */

export interface UseSSEReturn {
  /** Open an SSE connection (mock mode: streamUrl is the target URL, scanId/mode drive the simulation) */
  connect: (url: string, scanId: string, mode: ScanMode) => void
  /** Close the current SSE connection */
  disconnect: () => void
  /** Current connection status */
  statusRef: React.MutableRefObject<SSEStatus>
}

/* ── Mock SSE simulation (extracted from App.tsx) ─────────── */

const MODULE_LABELS: Record<ModuleName, string> = {
  headers: 'Security Headers',
  cookies: 'Cookie Flags',
  ssl_tls: 'SSL/TLS Certificate',
  information: 'Information Disclosure',
  cors: 'CORS Configuration',
  content: 'Page Content',
  http_config: 'HTTP Configuration',
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

function createMockSSEStream(
  targetUrl: string,
  mode: ScanMode,
  scanId: string,
  onEvent: (event: SSEEvent) => void,
): { cancel: () => void } {
  let cancelled = false

  const modules: ModuleName[] =
    mode === 'quick'
      ? ['headers', 'ssl_tls']
      : ['headers', 'cookies', 'ssl_tls', 'information', 'cors', 'content', 'http_config']

  // Randomised findings per module
  const moduleFindingsCounts: Record<ModuleName, number> = {
    headers: Math.floor(Math.random() * 4) + 1,
    cookies: Math.floor(Math.random() * 3),
    ssl_tls: Math.floor(Math.random() * 2),
    information: Math.floor(Math.random() * 3) + 1,
    cors: Math.floor(Math.random() * 2),
    content: Math.floor(Math.random() * 2),
    http_config: Math.floor(Math.random() * 2),
  }

  async function run() {
    // Start event
    await delay(300)
    if (cancelled) return
    onEvent({
      event: 'start',
      scan_id: scanId,
      progress: 0,
      message: `Initiating ${mode} scan on ${targetUrl}`,
      module: null,
    })

    // Process each module
    for (let i = 0; i < modules.length; i++) {
      if (cancelled) return
      const mod = modules[i]
      const baseProgress = Math.round((i / modules.length) * 100)

      // Module start
      await delay(600 + Math.random() * 400)
      if (cancelled) return
      onEvent({
        event: 'module_start',
        scan_id: scanId,
        progress: baseProgress,
        message: `Analyzing ${MODULE_LABELS[mod]}...`,
        module: mod,
      })

      // Module completed
      await delay(800 + Math.random() * 1200)
      if (cancelled) return
      const findings = moduleFindingsCounts[mod]
      const nextProgress = Math.round(((i + 1) / modules.length) * 90)
      onEvent({
        event: 'module_completed',
        scan_id: scanId,
        progress: nextProgress,
        message: `${MODULE_LABELS[mod]}: ${findings > 0 ? `${findings} issue(s) found` : 'All checks passed'}`,
        module: mod,
        findings_count: findings,
      })
    }

    // Scoring
    if (cancelled) return
    await delay(500)
    onEvent({
      event: 'scoring',
      scan_id: scanId,
      progress: 95,
      message: 'Calculating security score...',
      module: null,
    })

    // Complete
    await delay(600)
    if (cancelled) return
    onEvent({
      event: 'complete',
      scan_id: scanId,
      progress: 100,
      message: 'Security assessment finished',
      module: null,
      data: { grade: 'B', score: 72 },
    })
  }

  run()

  return {
    cancel: () => {
      cancelled = true
    },
  }
}

/* ── Real EventSource connection ──────────────────────────── */

function createRealSSEStream(
  streamUrl: string,
  onEvent: (event: SSEEvent) => void,
  onOpen?: () => void,
  onError?: (error: Event) => void,
): { cancel: () => void } {
  const eventSource = new EventSource(streamUrl)

  eventSource.onopen = () => {
    onOpen?.()
  }

  // Listen for all event types the backend emits
  const EVENT_TYPES: SSEEventType[] = [
    'start',
    'module_start',
    'module_completed',
    'scoring',
    'complete',
    'error',
  ]

  for (const eventType of EVENT_TYPES) {
    eventSource.addEventListener(eventType, (e: MessageEvent) => {
      try {
        const parsed: SSEEvent = JSON.parse(e.data)
        onEvent(parsed)

        // Auto-close on terminal events
        if (eventType === 'complete' || eventType === 'error') {
          eventSource.close()
        }
      } catch (err) {
        console.error(`[useSSE] Failed to parse ${eventType} event:`, err)
      }
    })
  }

  // Do NOT let EventSource auto-reconnect: the backend would start the scan
  // stream again for a still-running scan. Treat any error as terminal.
  eventSource.onerror = (e) => {
    eventSource.close()
    onError?.(e)
  }

  return {
    cancel: () => {
      eventSource.close()
    },
  }
}

/* ── useSSE hook ──────────────────────────────────────────── */

export function useSSE(options: UseSSEOptions): UseSSEReturn {
  const { onEvent, onOpen, onClose, onError, useMock = USE_MOCK } = options
  const cancelRef = useRef<{ cancel: () => void } | null>(null)
  const statusRef = useRef<SSEStatus>('idle')

  // Keep callback refs stable to avoid stale closures
  const onEventRef = useRef(onEvent)
  const onOpenRef = useRef(onOpen)
  const onCloseRef = useRef(onClose)
  const onErrorRef = useRef(onError)

  useEffect(() => { onEventRef.current = onEvent }, [onEvent])
  useEffect(() => { onOpenRef.current = onOpen }, [onOpen])
  useEffect(() => { onCloseRef.current = onClose }, [onClose])
  useEffect(() => { onErrorRef.current = onError }, [onError])

  const disconnect = useCallback(() => {
    cancelRef.current?.cancel()
    cancelRef.current = null
    statusRef.current = 'closed'
    onCloseRef.current?.()
  }, [])

  const connect = useCallback(
    (streamUrl: string, scanId: string, mode: ScanMode) => {
      // Close any existing connection
      if (cancelRef.current) {
        cancelRef.current.cancel()
        cancelRef.current = null
      }

      statusRef.current = 'connecting'

      const handleEvent = (event: SSEEvent) => {
        if (statusRef.current === 'connecting') {
          statusRef.current = 'connected'
        }
        onEventRef.current(event)

        // Mark as closed on terminal events
        if (event.event === 'complete' || event.event === 'error') {
          statusRef.current = 'closed'
          cancelRef.current = null
          onCloseRef.current?.()
        }
      }

      if (useMock) {
        // Mock mode — simulate SSE events locally
        statusRef.current = 'connected'
        onOpenRef.current?.()
        cancelRef.current = createMockSSEStream(
          streamUrl, // In mock mode, this is the target URL
          mode,
          scanId,
          handleEvent,
        )
      } else {
        // Real mode — connect to backend SSE endpoint
        cancelRef.current = createRealSSEStream(
          streamUrl,
          handleEvent,
          () => {
            statusRef.current = 'connected'
            onOpenRef.current?.()
          },
          (err) => {
            statusRef.current = 'error'
            onErrorRef.current?.(err)
          },
        )
      }
    },
    [useMock],
  )

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelRef.current?.cancel()
      cancelRef.current = null
    }
  }, [])

  return { connect, disconnect, statusRef }
}
