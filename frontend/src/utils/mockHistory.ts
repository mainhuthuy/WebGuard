/* ============================================================
   Mock scan history — demo data + local filter/sort/paginate.
   Used by useHistory in mock mode (VITE_USE_MOCK=true).
   ============================================================ */

import type { Grade, ScanHistoryItem, ScanMode } from '../types'

export type HistorySort = 'newest' | 'oldest' | 'score_desc' | 'score_asc'

export interface LocalHistoryQuery {
  search: string
  grade: Grade | 'all'
  sort: HistorySort
  page: number
  pageSize: number
}

export interface LocalHistoryPage {
  items: ScanHistoryItem[]
  total: number
  totalPages: number
}

export function generateMockHistory(now = Date.now()): ScanHistoryItem[] {
  const urls = [
    'https://example.com',
    'https://my-portfolio.dev',
    'https://api.internal.io',
    'https://staging.shop.vn',
    'https://blog.techstart.xyz',
    'https://dashboard.saas.app',
    'https://docs.openproject.org',
    'https://admin.crm-tool.com',
    'https://app.fintech.vn',
    'https://beta.healthcheck.io',
    'https://cdn.mediahost.net',
    'https://store.gadgets.co',
  ]
  const grades: Grade[] = ['A+', 'A', 'A', 'B', 'B', 'B', 'C', 'C', 'F', 'A', 'B', 'A+']
  const scores = [97, 88, 91, 74, 68, 72, 55, 48, 23, 85, 76, 95]
  const findingsCounts = [1, 3, 2, 5, 7, 6, 9, 11, 15, 4, 5, 0]
  const modes: ScanMode[] = [
    'full', 'full', 'quick', 'full', 'full', 'quick',
    'full', 'full', 'full', 'quick', 'full', 'quick',
  ]

  return urls.map((url, i) => ({
    scan_id: `scan_${1000 + i}`,
    url,
    mode: modes[i],
    status: 'completed' as const,
    grade: grades[i],
    score: scores[i],
    findings_count: findingsCounts[i],
    started_at: new Date(now - (i * 3 + 1) * 3600 * 1000).toISOString(),
    duration_ms: 2000 + ((i * 937) % 6000),
  }))
}

/** Filter, sort and paginate in memory — mirrors what GET /history does server-side */
export function queryLocalHistory(
  all: ScanHistoryItem[],
  { search, grade, sort, page, pageSize }: LocalHistoryQuery,
): LocalHistoryPage {
  let items = [...all]

  const q = search.trim().toLowerCase()
  if (q) items = items.filter((h) => h.url.toLowerCase().includes(q))
  if (grade !== 'all') items = items.filter((h) => h.grade === grade)

  items.sort((a, b) => {
    switch (sort) {
      case 'oldest':
        return new Date(a.started_at).getTime() - new Date(b.started_at).getTime()
      case 'score_desc':
        return (b.score ?? -1) - (a.score ?? -1)
      case 'score_asc':
        return (a.score ?? -1) - (b.score ?? -1)
      default:
        return new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
    }
  })

  const total = items.length
  const totalPages = total > 0 ? Math.ceil(total / pageSize) : 0
  const start = (page - 1) * pageSize
  return { items: items.slice(start, start + pageSize), total, totalPages }
}

/** Grades from best to worst */
export const GRADE_ORDER: Grade[] = ['A+', 'A', 'B', 'C', 'F']
