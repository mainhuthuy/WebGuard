import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { ApiError } from '../services'
import { useScan } from './useScan'

/* ── Mocks ───────────────────────────────────────────────── */

const createScan = vi.fn()
const cancelScan = vi.fn()

vi.mock('../services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services')>()
  return {
    ...actual,
    scanApi: {
      createScan: (...args: unknown[]) => createScan(...args),
      cancelScan: (...args: unknown[]) => cancelScan(...args),
      streamUrl: (id: string) => `/api/v1/scan/${id}/stream`,
    },
  }
})

type Listener = (e: MessageEvent) => void

class FakeEventSource {
  static instances: FakeEventSource[] = []
  onopen: (() => void) | null = null
  onerror: ((e: Event) => void) | null = null
  closed = false
  private listeners = new Map<string, Listener[]>()

  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, fn: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), fn])
  }

  close() {
    this.closed = true
  }

  /** Test helper: deliver a server event */
  emit(type: string, payload: Record<string, unknown>) {
    const event = { event: type, scan_id: 'scan-1', progress: 0, message: type, ...payload }
    for (const fn of this.listeners.get(type) ?? []) {
      fn({ data: JSON.stringify(event) } as MessageEvent)
    }
  }
}

const API_FINDING = {
  module: 'CORS',
  name: 'cors_wildcard',
  severity: 'high',
  description: 'Wildcard origin',
  remediation: 'Use an allowlist',
  url: 'https://example.com',
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  createScan.mockReset()
  cancelScan.mockReset()
  cancelScan.mockResolvedValue({})
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

/* ── Real (backend) mode ─────────────────────────────────── */

describe('useScan — backend mode', () => {
  async function startAndConnect() {
    createScan.mockResolvedValue({ scan_id: 'scan-1', target_url: 'https://example.com' })
    const hook = renderHook(() => useScan({ useMock: false }))
    act(() => hook.result.current.startScan('https://example.com', 'full'))
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
    return { hook, es: FakeEventSource.instances[0] }
  }

  it('creates the scan, then streams from its URL', async () => {
    const { hook, es } = await startAndConnect()
    expect(createScan).toHaveBeenCalledWith('https://example.com', 'full')
    expect(es.url).toBe('/api/v1/scan/scan-1/stream')
    expect(hook.result.current.phase).toBe('scanning')
    expect(hook.result.current.scanning).toBe(true)
  })

  it('sends the chosen mode to the backend and shows only its modules', async () => {
    createScan.mockResolvedValue({ scan_id: 'scan-1' })
    const { result } = renderHook(() => useScan({ useMock: false }))
    act(() => result.current.startScan('https://example.com', 'quick'))

    expect(createScan).toHaveBeenCalledWith('https://example.com', 'quick')
    expect(result.current.modules.map((m) => m.id)).toEqual(['headers', 'ssl_tls'])
    await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
  })

  it('updates module state and progress from stream events', async () => {
    const { hook, es } = await startAndConnect()

    act(() => es.emit('module_start', { module: 'CORS', progress: 70 }))
    const cors = () => hook.result.current.modules.find((m) => m.id === 'cors')
    expect(cors()?.status).toBe('active')
    expect(hook.result.current.progress).toBe(70)

    act(() => es.emit('module_completed', { module: 'CORS', progress: 85, findings: [API_FINDING] }))
    expect(cors()?.status).toBe('completed')
    expect(cors()?.findingsCount).toBe(1)
    expect(hook.result.current.logs).toHaveLength(2)
  })

  it('builds the final result from the complete event', async () => {
    const { hook, es } = await startAndConnect()

    act(() =>
      es.emit('complete', {
        progress: 100,
        findings: [API_FINDING],
        data: { scoring: { score: 90, grade: 'A', total_findings: 1 } },
      }),
    )

    const { result, phase, completed } = hook.result.current
    expect(phase).toBe('completed')
    expect(completed).toBe(true)
    expect(result?.grade).toBe('A')
    expect(result?.score).toBe(90)
    expect(result?.url).toBe('https://example.com')
    expect(result?.findings[0]).toMatchObject({ module: 'cors', title: 'cors_wildcard' })
    expect(result?.summary.high).toBe(1)
    expect(es.closed).toBe(true)
  })

  it('goes to errored when the stream sends an error event', async () => {
    const { hook, es } = await startAndConnect()
    act(() => es.emit('error', { message: 'Scan blew up' }))
    expect(hook.result.current.phase).toBe('errored')
    expect(hook.result.current.errored).toBe(true)
    expect(hook.result.current.errorMessage).toBe('Scan blew up')
  })

  it('marks the module that was running as failed when the scan errors', async () => {
    const { hook, es } = await startAndConnect()
    act(() => es.emit('module_start', { module: 'headers', progress: 10 }))
    act(() => es.emit('error', { message: 'boom' }))
    const status = (id: string) => hook.result.current.modules.find((m) => m.id === id)?.status
    expect(status('headers')).toBe('error')
    expect(status('cookies')).toBe('pending')
  })

  it('goes to errored when the connection drops mid-scan', async () => {
    const { hook, es } = await startAndConnect()
    act(() => es.onerror?.(new Event('error')))
    expect(hook.result.current.phase).toBe('errored')
    expect(hook.result.current.errorMessage).toMatch(/lost connection/i)
    expect(es.closed).toBe(true)
  })

  it('surfaces a failure to create the scan', async () => {
    createScan.mockRejectedValue(new ApiError('Localhost is not allowed', 422, 'VALIDATION_ERROR'))
    const { result } = renderHook(() => useScan({ useMock: false }))
    act(() => result.current.startScan('http://localhost', 'full'))

    await waitFor(() => expect(result.current.phase).toBe('errored'))
    expect(result.current.errorMessage).toBe('Localhost is not allowed')
    expect(result.current.logs[0].message).toBe('Localhost is not allowed')
    expect(FakeEventSource.instances).toHaveLength(0)
  })

  it('cancelling stops the stream and cancels the scan on the server', async () => {
    const { hook, es } = await startAndConnect()
    act(() => hook.result.current.cancelScan())

    expect(es.closed).toBe(true)
    expect(cancelScan).toHaveBeenCalledWith('scan-1')
    expect(hook.result.current.phase).toBe('idle')
  })

  it('ignores a create-scan response that arrives after cancel', async () => {
    let resolveCreate: (v: unknown) => void = () => undefined
    createScan.mockReturnValue(new Promise((r) => (resolveCreate = r)))
    const { result } = renderHook(() => useScan({ useMock: false }))

    act(() => result.current.startScan('https://example.com', 'full'))
    act(() => result.current.cancelScan())
    await act(async () => resolveCreate({ scan_id: 'late' }))

    expect(FakeEventSource.instances).toHaveLength(0)
    expect(result.current.phase).toBe('idle')
    expect(cancelScan).not.toHaveBeenCalled()
  })

  it('reset clears all state', async () => {
    const { hook, es } = await startAndConnect()
    act(() => es.emit('module_start', { module: 'headers', progress: 10 }))
    act(() => hook.result.current.reset())

    expect(hook.result.current.phase).toBe('idle')
    expect(hook.result.current.modules).toEqual([])
    expect(hook.result.current.logs).toEqual([])
    expect(hook.result.current.scanUrl).toBe('')
  })
})

/* ── Mock mode ───────────────────────────────────────────── */

describe('useScan — mock mode', () => {
  it('runs a simulated quick scan to completion without touching the API', async () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => useScan({ useMock: true }))

    act(() => result.current.startScan('https://example.com', 'quick'))
    expect(result.current.modules.map((m) => m.id)).toEqual(['headers', 'ssl_tls'])

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })

    expect(result.current.phase).toBe('completed')
    expect(result.current.progress).toBe(100)
    expect(result.current.result?.url).toBe('https://example.com')
    expect(result.current.result?.mode).toBe('quick')
    expect(createScan).not.toHaveBeenCalled()
  })
})
