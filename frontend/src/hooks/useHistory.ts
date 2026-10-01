/* ============================================================
   useHistory — scan history list, filters, pagination, stats
   Real mode: server-side filtering/sorting/paging via GET /history
   and GET /history/stats. Mock mode: same behaviour on local data.
   ============================================================ */

import { useState, useEffect, useCallback, useRef } from 'react'
import { scanApi, toApiError, mapHistoryItem, toGrade } from '../services'
import { USE_MOCK } from '../config'
import {
  GRADE_ORDER,
  generateMockHistory,
  queryLocalHistory,
  type HistorySort,
} from '../utils/mockHistory'
import type { Grade, HistoryQuery, ScanHistoryItem } from '../types'

export type { HistorySort }

export interface HistoryStats {
  total: number
  completed: number
  /** Rounded average score of completed scans, null if none */
  avgScore: number | null
  /** Best grade seen, null if none */
  bestGrade: Grade | null
}

export interface UseHistoryOptions {
  /** Rows per page. @default 10 */
  pageSize?: number
  /** Use local mock data. @default USE_MOCK */
  useMock?: boolean
  /** Debounce for the search box in ms. @default 300 */
  searchDebounceMs?: number
}

export interface UseHistoryReturn {
  items: ScanHistoryItem[]
  total: number
  totalPages: number
  page: number
  setPage: (page: number) => void
  search: string
  setSearch: (value: string) => void
  grade: Grade | 'all'
  setGrade: (value: Grade | 'all') => void
  sort: HistorySort
  setSort: (value: HistorySort) => void
  stats: HistoryStats | null
  loading: boolean
  error: string | null
  /** Re-fetch list and stats */
  refresh: () => void
  /** Delete one scan, then refresh. Resolves true on success. */
  deleteScan: (scanId: string) => Promise<boolean>
}

const SORT_PARAMS: Record<HistorySort, Pick<HistoryQuery, 'sort_by' | 'sort_order'>> = {
  newest: { sort_by: 'created_at', sort_order: 'desc' },
  oldest: { sort_by: 'created_at', sort_order: 'asc' },
  score_desc: { sort_by: 'score', sort_order: 'desc' },
  score_asc: { sort_by: 'score', sort_order: 'asc' },
}

function statsFromItems(all: ScanHistoryItem[]): HistoryStats {
  const scored = all.filter((h) => h.score !== null)
  const avg = scored.length
    ? Math.round(scored.reduce((s, h) => s + (h.score ?? 0), 0) / scored.length)
    : null
  const best = all.reduce<Grade | null>((acc, h) => {
    if (!h.grade) return acc
    return !acc || GRADE_ORDER.indexOf(h.grade) < GRADE_ORDER.indexOf(acc) ? h.grade : acc
  }, null)
  return {
    total: all.length,
    completed: all.filter((h) => h.status === 'completed').length,
    avgScore: avg,
    bestGrade: best,
  }
}

export function useHistory(options: UseHistoryOptions = {}): UseHistoryReturn {
  const { pageSize = 10, useMock = USE_MOCK, searchDebounceMs = 300 } = options

  const [page, setPage] = useState(1)
  const [search, setSearchState] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [grade, setGradeState] = useState<Grade | 'all'>('all')
  const [sort, setSortState] = useState<HistorySort>('newest')

  const [items, setItems] = useState<ScanHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [stats, setStats] = useState<HistoryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  /** Bumped to force a re-fetch (refresh / after delete) */
  const [reloadKey, setReloadKey] = useState(0)

  const mockData = useRef<ScanHistoryItem[]>(useMock ? generateMockHistory() : [])

  // Debounce the search text, and go back to page 1 when it settles
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, searchDebounceMs)
    return () => clearTimeout(t)
  }, [search, searchDebounceMs])

  const setSearch = useCallback((value: string) => setSearchState(value), [])
  const setGrade = useCallback((value: Grade | 'all') => {
    setGradeState(value)
    setPage(1)
  }, [])
  const setSort = useCallback((value: HistorySort) => {
    setSortState(value)
    setPage(1)
  }, [])

  // Load the list
  useEffect(() => {
    if (useMock) {
      const res = queryLocalHistory(mockData.current, {
        search: debouncedSearch,
        grade,
        sort,
        page,
        pageSize,
      })
      setItems(res.items)
      setTotal(res.total)
      setTotalPages(res.totalPages)
      setStats(statsFromItems(mockData.current))
      setLoading(false)
      setError(null)
      return
    }

    let ignore = false
    setLoading(true)
    scanApi
      .getHistory({
        page,
        page_size: pageSize,
        search_url: debouncedSearch.trim() || undefined,
        grade: grade === 'all' ? undefined : grade,
        ...SORT_PARAMS[sort],
      })
      .then((res) => {
        if (ignore) return
        setItems(res.items.map(mapHistoryItem))
        setTotal(res.total)
        setTotalPages(res.total_pages)
        setError(null)
      })
      .catch((err) => {
        if (ignore) return
        setError(toApiError(err).message)
      })
      .finally(() => {
        if (!ignore) setLoading(false)
      })
    return () => {
      ignore = true
    }
  }, [useMock, page, pageSize, debouncedSearch, grade, sort, reloadKey])

  // Load the stats (independent of the filters)
  useEffect(() => {
    if (useMock) return
    let ignore = false
    scanApi
      .getHistoryStats()
      .then((s) => {
        if (ignore) return
        const best = GRADE_ORDER.find((g) => (s.grade_distribution[g] ?? 0) > 0) ?? null
        setStats({
          total: s.total_scans,
          completed: s.completed_scans,
          avgScore: s.average_score === null ? null : Math.round(s.average_score),
          bestGrade: best ? toGrade(best) : null,
        })
      })
      .catch(() => {
        // Stats are decorative; the list error banner already covers connectivity problems
        if (!ignore) setStats(null)
      })
    return () => {
      ignore = true
    }
  }, [useMock, reloadKey])

  const refresh = useCallback(() => setReloadKey((k) => k + 1), [])

  const deleteScan = useCallback(
    async (scanId: string): Promise<boolean> => {
      try {
        if (useMock) {
          mockData.current = mockData.current.filter((h) => h.scan_id !== scanId)
        } else {
          await scanApi.deleteScan(scanId)
        }
        // Step back a page if we just removed the last row of the last page
        if (items.length === 1 && page > 1) setPage(page - 1)
        setReloadKey((k) => k + 1)
        return true
      } catch (err) {
        setError(toApiError(err).message)
        return false
      }
    },
    [useMock, items.length, page],
  )

  return {
    items,
    total,
    totalPages,
    page,
    setPage,
    search,
    setSearch,
    grade,
    setGrade,
    sort,
    setSort,
    stats,
    loading,
    error,
    refresh,
    deleteScan,
  }
}
