import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { ApiError } from '../services'
import { useHistory } from './useHistory'
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

function apiItem(id: string, overrides: Partial<ApiHistoryItem> = {}): ApiHistoryItem {
  return {
    id,
    target_url: `https://${id}.example.com`,
    mode: 'full',
    status: 'completed',
    score: 80,
    grade: 'B',
    total_findings: 3,
    created_at: '2026-10-01T03:00:00',
    completed_at: '2026-10-01T03:00:02',
    duration_seconds: 2,
    ...overrides,
  }
}

function page(items: ApiHistoryItem[], extra: Record<string, unknown> = {}) {
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

const STATS = {
  total_scans: 12,
  completed_scans: 10,
  failed_scans: 1,
  cancelled_scans: 1,
  average_score: 71.6,
  grade_distribution: { B: 4, C: 3, A: 2 },
}

beforeEach(() => {
  getHistory.mockReset()
  getHistoryStats.mockReset()
  deleteScan.mockReset()
  getHistory.mockResolvedValue(page([apiItem('a'), apiItem('b')]))
  getHistoryStats.mockResolvedValue(STATS)
  deleteScan.mockResolvedValue({ deleted: true })
})

const render = (opts = {}) =>
  renderHook(() => useHistory({ useMock: false, searchDebounceMs: 5, ...opts }))

describe('useHistory — backend mode', () => {
  it('loads and maps the first page', async () => {
    const { result } = render()
    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.items.map((i) => i.scan_id)).toEqual(['a', 'b'])
    expect(result.current.items[0]).toMatchObject({ url: 'https://a.example.com', mode: 'full' })
    expect(getHistory).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        page_size: 10,
        sort_by: 'created_at',
        sort_order: 'desc',
        search_url: undefined,
        grade: undefined,
      }),
    )
  })

  it('derives stats from the stats endpoint', async () => {
    const { result } = render()
    await waitFor(() => expect(result.current.stats).not.toBeNull())
    expect(result.current.stats).toEqual({
      total: 12,
      completed: 10,
      avgScore: 72,
      bestGrade: 'A',
    })
  })

  it('sends filters and sort to the server and resets to page 1', async () => {
    getHistory.mockResolvedValue(page([apiItem('a')], { total_pages: 3, total: 25 }))
    const { result } = render()
    await waitFor(() => expect(result.current.totalPages).toBe(3))

    act(() => result.current.setPage(2))
    await waitFor(() => expect(getHistory).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })))

    act(() => result.current.setGrade('F'))
    await waitFor(() =>
      expect(getHistory).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, grade: 'F' })),
    )

    act(() => result.current.setSort('score_asc'))
    await waitFor(() =>
      expect(getHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ sort_by: 'score', sort_order: 'asc' }),
      ),
    )
  })

  it('debounces the search box and trims the term', async () => {
    const { result } = render({ searchDebounceMs: 30 })
    await waitFor(() => expect(result.current.loading).toBe(false))
    getHistory.mockClear()

    act(() => result.current.setSearch('  exa'))
    act(() => result.current.setSearch('  example '))
    expect(getHistory).not.toHaveBeenCalled()

    await waitFor(() =>
      expect(getHistory).toHaveBeenLastCalledWith(
        expect.objectContaining({ search_url: 'example' }),
      ),
    )
    expect(getHistory).toHaveBeenCalledTimes(1)
  })

  it('surfaces a list error', async () => {
    getHistory.mockRejectedValue(new ApiError('Cannot reach the server', null, 'NETWORK_ERROR'))
    const { result } = render()
    await waitFor(() => expect(result.current.error).toBe('Cannot reach the server'))
    expect(result.current.items).toEqual([])
    expect(result.current.loading).toBe(false)
  })

  it('keeps working when only the stats request fails', async () => {
    getHistoryStats.mockRejectedValue(new Error('stats down'))
    const { result } = render()
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.items).toHaveLength(2)
    expect(result.current.stats).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('deletes a scan and reloads', async () => {
    const { result } = render()
    await waitFor(() => expect(result.current.loading).toBe(false))
    getHistory.mockClear()

    let ok = false
    await act(async () => {
      ok = await result.current.deleteScan('a')
    })
    expect(ok).toBe(true)
    expect(deleteScan).toHaveBeenCalledWith('a')
    await waitFor(() => expect(getHistory).toHaveBeenCalledTimes(1))
  })

  it('reports a failed delete without reloading', async () => {
    deleteScan.mockRejectedValue(new ApiError('Not found', 404, 'SCAN_NOT_FOUND'))
    const { result } = render()
    await waitFor(() => expect(result.current.loading).toBe(false))

    let ok = true
    await act(async () => {
      ok = await result.current.deleteScan('missing')
    })
    expect(ok).toBe(false)
    expect(result.current.error).toBe('Not found')
  })

  it('steps back a page after deleting the last row of the last page', async () => {
    getHistory.mockResolvedValue(page([apiItem('only')], { total_pages: 2, total: 11 }))
    const { result } = render()
    await waitFor(() => expect(result.current.loading).toBe(false))
    act(() => result.current.setPage(2))
    await waitFor(() => expect(getHistory).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2 })))

    await act(async () => {
      await result.current.deleteScan('only')
    })
    await waitFor(() => expect(result.current.page).toBe(1))
  })

  it('ignores a stale response that arrives after a newer request', async () => {
    let resolveFirst: (v: unknown) => void = () => undefined
    getHistory.mockReset()
    getHistory.mockReturnValueOnce(new Promise((r) => (resolveFirst = r)))
    getHistory.mockResolvedValue(page([apiItem('fresh')]))

    const { result } = render()
    act(() => result.current.setGrade('A')) // triggers a second request
    await waitFor(() => expect(result.current.items.map((i) => i.scan_id)).toEqual(['fresh']))

    await act(async () => resolveFirst(page([apiItem('stale')])))
    expect(result.current.items.map((i) => i.scan_id)).toEqual(['fresh'])
  })
})

describe('useHistory — mock mode', () => {
  it('serves local data without touching the API', async () => {
    const { result } = renderHook(() => useHistory({ useMock: true, pageSize: 5 }))
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.items).toHaveLength(5)
    expect(result.current.totalPages).toBeGreaterThan(1)
    expect(result.current.stats?.total).toBe(result.current.total)
    expect(getHistory).not.toHaveBeenCalled()
    expect(getHistoryStats).not.toHaveBeenCalled()
  })

  it('filters and deletes locally', async () => {
    const { result } = renderHook(() => useHistory({ useMock: true, pageSize: 50 }))
    await waitFor(() => expect(result.current.loading).toBe(false))
    const before = result.current.total

    act(() => result.current.setGrade('F'))
    await waitFor(() => expect(result.current.items.every((i) => i.grade === 'F')).toBe(true))
    const victim = result.current.items[0].scan_id

    await act(async () => {
      await result.current.deleteScan(victim)
    })
    await waitFor(() => expect(result.current.stats?.total).toBe(before - 1))
    expect(deleteScan).not.toHaveBeenCalled()
  })
})
