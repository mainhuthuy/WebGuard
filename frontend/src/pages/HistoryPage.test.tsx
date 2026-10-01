import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import HistoryPage from './HistoryPage'
import type { ApiHistoryItem } from '../types'

const getHistory = vi.fn()
const getHistoryStats = vi.fn()
const deleteScan = vi.fn()

vi.mock('../services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services')>()
  return {
    ...actual,
    scanApi: {
      getHistory: (...args: unknown[]) => getHistory(...args),
      getHistoryStats: (...args: unknown[]) => getHistoryStats(...args),
      deleteScan: (...args: unknown[]) => deleteScan(...args),
    },
  }
})

const completed: ApiHistoryItem = {
  id: 'done-1',
  target_url: 'https://done.example.com',
  mode: 'quick',
  status: 'completed',
  score: 82,
  grade: 'B',
  total_findings: 4,
  created_at: '2026-10-01T03:00:00',
  completed_at: '2026-10-01T03:00:02',
  duration_seconds: 2,
}
const failed: ApiHistoryItem = {
  ...completed,
  id: 'fail-1',
  target_url: 'https://down.example.com',
  status: 'failed',
  score: null,
  grade: null,
  total_findings: 0,
}

function pageOf(items: ApiHistoryItem[], extra: Record<string, unknown> = {}) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 10,
    total_pages: items.length ? 1 : 0,
    has_next: false,
    has_prev: false,
    ...extra,
  }
}

beforeEach(() => {
  getHistory.mockReset()
  getHistoryStats.mockReset()
  deleteScan.mockReset()
  getHistory.mockResolvedValue(pageOf([completed, failed]))
  getHistoryStats.mockResolvedValue({
    total_scans: 2,
    completed_scans: 1,
    failed_scans: 1,
    cancelled_scans: 0,
    average_score: 82,
    grade_distribution: { B: 1 },
  })
  deleteScan.mockResolvedValue({ deleted: true })
})

describe('HistoryPage', () => {
  it('lists scans from the API with grade, score, mode and stats', async () => {
    render(<HistoryPage />)
    const row = await screen.findByText('https://done.example.com')
    const tr = row.closest('tr') as HTMLElement

    expect(within(tr).getByText('B')).toBeInTheDocument()
    expect(within(tr).getByText('82')).toBeInTheDocument()
    expect(within(tr).getByText('quick')).toBeInTheDocument()
    expect(within(tr).getByText('4 issues')).toBeInTheDocument()

    // Stats come from /history/stats
    await waitFor(() => expect(screen.getByText('Total Scans').previousElementSibling).toHaveTextContent('2'))
  })

  it('shows the status instead of a grade for scans that did not complete', async () => {
    render(<HistoryPage />)
    const tr = (await screen.findByText('https://down.example.com')).closest('tr') as HTMLElement
    expect(within(tr).getByText('Failed')).toBeInTheDocument()
  })

  it('opens a completed scan on row click, passing the item', async () => {
    const onViewScan = vi.fn()
    render(<HistoryPage onViewScan={onViewScan} />)
    fireEvent.click(await screen.findByText('https://done.example.com'))

    expect(onViewScan).toHaveBeenCalledTimes(1)
    expect(onViewScan.mock.calls[0][0]).toMatchObject({ scan_id: 'done-1', url: 'https://done.example.com' })
  })

  it('does not open scans that did not complete', async () => {
    const onViewScan = vi.fn()
    render(<HistoryPage onViewScan={onViewScan} />)
    fireEvent.click(await screen.findByText('https://down.example.com'))
    expect(onViewScan).not.toHaveBeenCalled()
  })

  it('asks for confirmation before deleting, then deletes', async () => {
    const onViewScan = vi.fn()
    render(<HistoryPage onViewScan={onViewScan} />)
    await screen.findByText('https://done.example.com')

    fireEvent.click(screen.getByLabelText('Delete scan of https://done.example.com'))
    expect(onViewScan).not.toHaveBeenCalled() // delete must not trigger the row click
    expect(screen.getByText('Delete scan?')).toBeInTheDocument()
    expect(deleteScan).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(deleteScan).toHaveBeenCalledWith('done-1'))
  })

  it('cancelling the confirmation keeps the scan', async () => {
    render(<HistoryPage />)
    await screen.findByText('https://done.example.com')
    fireEvent.click(screen.getByLabelText('Delete scan of https://done.example.com'))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(deleteScan).not.toHaveBeenCalled()
  })

  it('shows an empty state', async () => {
    getHistory.mockResolvedValue(pageOf([]))
    render(<HistoryPage />)
    expect(await screen.findByText('No scans yet')).toBeInTheDocument()
  })

  it('shows a "no matching" state when a filter returns nothing', async () => {
    render(<HistoryPage />)
    await screen.findByText('https://done.example.com')
    getHistory.mockResolvedValue(pageOf([]))
    fireEvent.click(screen.getByRole('button', { name: 'F' }))
    expect(await screen.findByText('No matching scans')).toBeInTheDocument()
    expect(getHistory).toHaveBeenLastCalledWith(expect.objectContaining({ grade: 'F' }))
  })

  it('shows an error banner when the request fails', async () => {
    getHistory.mockRejectedValue(new Error('Cannot reach the server'))
    render(<HistoryPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the server')
  })

  it('shows an error passed in by the parent (e.g. opening a scan failed)', async () => {
    render(<HistoryPage openError="Scan not found" />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Scan not found')
  })

  it('paginates', async () => {
    getHistory.mockResolvedValue(pageOf([completed], { total_pages: 3, total: 25 }))
    render(<HistoryPage />)
    await screen.findByText(/Page 1 of 3/)

    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    await waitFor(() => expect(getHistory).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })))
  })
})
