import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { ApiError } from './services'
import App from './App'
import { makeApiScanDetail } from './test/fixtures'

/* ── Mocks ───────────────────────────────────────────────── */

const createScan = vi.fn()
const getScan = vi.fn()
const cancelScan = vi.fn()
const getHistory = vi.fn()
const getHistoryStats = vi.fn()

vi.mock('./services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./services')>()
  return {
    ...actual,
    scanApi: {
      createScan: (...a: unknown[]) => createScan(...a),
      getScan: (...a: unknown[]) => getScan(...a),
      cancelScan: (...a: unknown[]) => cancelScan(...a),
      streamUrl: (id: string) => `/api/v1/scan/${id}/stream`,
      getHistory: (...a: unknown[]) => getHistory(...a),
      getHistoryStats: (...a: unknown[]) => getHistoryStats(...a),
    },
  }
})

type Listener = (e: MessageEvent) => void

class FakeEventSource {
  static instances: FakeEventSource[] = []
  onopen: (() => void) | null = null
  onerror: ((e: Event) => void) | null = null
  private listeners = new Map<string, Listener[]>()
  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }
  addEventListener(type: string, fn: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), fn])
  }
  close() {}
  emit(type: string, payload: Record<string, unknown>) {
    const event = { event: type, scan_id: 'scan-1', progress: 0, message: type, ...payload }
    for (const fn of this.listeners.get(type) ?? []) fn({ data: JSON.stringify(event) } as MessageEvent)
  }
}

const HISTORY_ITEM = {
  id: 'done-1',
  target_url: 'https://done.example.com',
  mode: 'full',
  status: 'completed',
  score: 90,
  grade: 'A',
  total_findings: 1,
  created_at: '2026-10-01T03:00:00',
  completed_at: '2026-10-01T03:00:02',
  duration_seconds: 2,
}

beforeEach(() => {
  FakeEventSource.instances = []
  vi.stubGlobal('EventSource', FakeEventSource)
  for (const fn of [createScan, getScan, cancelScan, getHistory, getHistoryStats]) fn.mockReset()
  cancelScan.mockResolvedValue({})
  createScan.mockResolvedValue({ scan_id: 'scan-1', target_url: 'https://example.com', mode: 'full' })
  getHistory.mockResolvedValue({
    items: [HISTORY_ITEM],
    total: 1,
    page: 1,
    page_size: 10,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  })
  getHistoryStats.mockResolvedValue({
    total_scans: 1,
    completed_scans: 1,
    failed_scans: 0,
    cancelled_scans: 0,
    average_score: 90,
    grade_distribution: { A: 1 },
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

/* ── Helpers ─────────────────────────────────────────────── */

const nav = (label: string) =>
  within(document.getElementById('app-sidebar') as HTMLElement).getByText(label)

async function startScan(url = 'https://example.com') {
  fireEvent.change(screen.getByPlaceholderText('https://example.com'), { target: { value: url } })
  fireEvent.click(screen.getByRole('button', { name: /scan target/i }))
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1))
  return FakeEventSource.instances[0]
}

/* ── Tests ───────────────────────────────────────────────── */

describe('App — scan flow', () => {
  it('starts a scan with the chosen mode and shows live progress', async () => {
    render(<App />)
    fireEvent.click(screen.getByText('Quick Scan'))
    await startScan()

    expect(createScan).toHaveBeenCalledWith('https://example.com', 'quick')
    expect(screen.getByText('Scanning Target...')).toBeInTheDocument()
    // quick mode: only two modules listed
    expect(screen.getByText('Security Headers')).toBeInTheDocument()
    expect(screen.queryByText('Cookie Flags')).not.toBeInTheDocument()
  })

  it('goes through to the results page and back to a fresh scan form', async () => {
    render(<App />)
    const es = await startScan()

    es.emit('complete', {
      progress: 100,
      findings: [
        {
          module: 'headers',
          name: 'x-frame-options',
          severity: 'medium',
          description: 'No XFO',
          remediation: 'Thêm header: X-Frame-Options: DENY',
          url: 'https://example.com',
        },
      ],
      data: { scoring: { score: 95, grade: 'A+', total_findings: 1 } },
    })

    fireEvent.click(await screen.findByRole('button', { name: /view results/i }))
    expect(await screen.findByText('A+')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /new scan/i }))
    expect(await screen.findByPlaceholderText('https://example.com')).toBeInTheDocument()
  })

  it('"New Scan" in the sidebar returns to the live progress while scanning', async () => {
    render(<App />)
    await startScan()

    fireEvent.click(nav('Scan History'))
    await screen.findByText('https://done.example.com')

    fireEvent.click(nav('New Scan'))
    expect(await screen.findByText('Scanning Target...')).toBeInTheDocument()
    expect(createScan).toHaveBeenCalledTimes(1) // the scan was not restarted
  })

  it('shows why a scan failed and lets the user try again', async () => {
    createScan.mockRejectedValue(new ApiError('Localhost is not allowed', 422, 'VALIDATION_ERROR'))
    render(<App />)
    fireEvent.change(screen.getByPlaceholderText('https://example.com'), {
      target: { value: 'https://example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /scan target/i }))

    expect(await screen.findByText('Scan Failed')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Localhost is not allowed')

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByPlaceholderText('https://example.com')).toBeInTheDocument()
  })

  it('cancelling a running scan returns to the form and cancels it on the server', async () => {
    render(<App />)
    await startScan()
    fireEvent.click(screen.getByRole('button', { name: /cancel scan/i }))

    expect(await screen.findByPlaceholderText('https://example.com')).toBeInTheDocument()
    expect(cancelScan).toHaveBeenCalledWith('scan-1')
  })
})

describe('App — history', () => {
  it('opens a past scan, loaded from the API, and returns to the history', async () => {
    getScan.mockResolvedValue(
      makeApiScanDetail({ scan_id: 'done-1', target_url: 'https://done.example.com' }),
    )
    render(<App />)
    fireEvent.click(nav('Scan History'))
    fireEvent.click(await screen.findByText('https://done.example.com'))

    await waitFor(() => expect(getScan).toHaveBeenCalledWith('done-1'))
    expect(await screen.findByText('Back to History')).toBeInTheDocument()
    expect(screen.getByText('https://done.example.com')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Back to History'))
    expect(await screen.findByText('Scan History', { selector: 'h2' })).toBeInTheDocument()
  })

  it('stays on the history and shows an error when the scan cannot be loaded', async () => {
    getScan.mockRejectedValue(new ApiError('Scan not found', 404, 'SCAN_NOT_FOUND'))
    render(<App />)
    fireEvent.click(nav('Scan History'))
    fireEvent.click(await screen.findByText('https://done.example.com'))

    expect(await screen.findByRole('alert')).toHaveTextContent('Scan not found')
    expect(screen.queryByText('Back to History')).not.toBeInTheDocument()
  })
})

describe('App — about', () => {
  it('lazy-loads the About page', async () => {
    render(<App />)
    fireEvent.click(nav('About & Disclaimer'))
    expect(await screen.findByText('Authorized use only')).toBeInTheDocument()
  })
})
