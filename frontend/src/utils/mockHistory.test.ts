import { describe, it, expect } from 'vitest'
import { generateMockHistory, queryLocalHistory, type LocalHistoryQuery } from './mockHistory'

const NOW = new Date('2026-10-01T12:00:00Z').getTime()
const all = generateMockHistory(NOW)

const base: LocalHistoryQuery = { search: '', grade: 'all', sort: 'newest', page: 1, pageSize: 5 }

describe('generateMockHistory', () => {
  it('is deterministic for a given clock', () => {
    expect(generateMockHistory(NOW)).toEqual(generateMockHistory(NOW))
  })

  it('produces completed scans with grade and score', () => {
    expect(all.length).toBeGreaterThan(5)
    expect(all.every((h) => h.status === 'completed' && h.grade && h.score !== null)).toBe(true)
  })
})

describe('queryLocalHistory', () => {
  it('paginates', () => {
    const p1 = queryLocalHistory(all, base)
    const p3 = queryLocalHistory(all, { ...base, page: 3 })
    expect(p1.items).toHaveLength(5)
    expect(p1.total).toBe(all.length)
    expect(p1.totalPages).toBe(Math.ceil(all.length / 5))
    expect(p3.items).toHaveLength(all.length - 10)
  })

  it('sorts newest first by default and oldest first on request', () => {
    const newest = queryLocalHistory(all, { ...base, pageSize: 100 }).items
    const oldest = queryLocalHistory(all, { ...base, pageSize: 100, sort: 'oldest' }).items
    expect(newest[0].scan_id).toBe(oldest[oldest.length - 1].scan_id)
  })

  it('sorts by score in both directions', () => {
    const desc = queryLocalHistory(all, { ...base, pageSize: 100, sort: 'score_desc' }).items
    const asc = queryLocalHistory(all, { ...base, pageSize: 100, sort: 'score_asc' }).items
    expect(desc[0].score).toBe(Math.max(...all.map((h) => h.score ?? 0)))
    expect(asc[0].score).toBe(Math.min(...all.map((h) => h.score ?? 0)))
  })

  it('filters by grade', () => {
    const res = queryLocalHistory(all, { ...base, pageSize: 100, grade: 'F' })
    expect(res.total).toBeGreaterThan(0)
    expect(res.items.every((h) => h.grade === 'F')).toBe(true)
  })

  it('searches the URL case-insensitively', () => {
    const res = queryLocalHistory(all, { ...base, search: '  EXAMPLE.COM ' })
    expect(res.items.map((h) => h.url)).toEqual(['https://example.com'])
  })

  it('returns an empty page when nothing matches', () => {
    const res = queryLocalHistory(all, { ...base, search: 'no-such-site' })
    expect(res).toEqual({ items: [], total: 0, totalPages: 0 })
  })
})
