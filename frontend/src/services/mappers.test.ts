import { describe, it, expect } from 'vitest'
import {
  toUtcIso,
  toGrade,
  toModuleName,
  mapFinding,
  mapScanDetail,
  mapHistoryItem,
  extractSnippet,
  summarize,
} from './mappers'
import { makeApiScanDetail, makeFinding } from '../test/fixtures'

describe('toUtcIso', () => {
  it('appends Z to naive backend datetimes', () => {
    expect(toUtcIso('2026-10-01T03:05:08.191297')).toBe('2026-10-01T03:05:08.191297Z')
  })

  it('keeps values that already carry an offset', () => {
    expect(toUtcIso('2026-10-01T03:05:08Z')).toBe('2026-10-01T03:05:08Z')
    expect(toUtcIso('2026-10-01T03:05:08+07:00')).toBe('2026-10-01T03:05:08+07:00')
  })

  it('returns undefined for empty values', () => {
    expect(toUtcIso(null)).toBeUndefined()
    expect(toUtcIso('')).toBeUndefined()
  })
})

describe('toGrade', () => {
  it('passes valid grades through', () => {
    expect(toGrade('A+')).toBe('A+')
    expect(toGrade('C')).toBe('C')
  })

  it('falls back to F for unknown or missing grades', () => {
    expect(toGrade('D')).toBe('F')
    expect(toGrade(null)).toBe('F')
    expect(toGrade(undefined)).toBe('F')
  })
})

describe('toModuleName', () => {
  it('lower-cases backend names', () => {
    expect(toModuleName('CORS')).toBe('cors')
    expect(toModuleName('ssl_tls')).toBe('ssl_tls')
  })

  it('falls back to information for unknown modules', () => {
    expect(toModuleName('mystery')).toBe('information')
    expect(toModuleName(null)).toBe('information')
  })
})

describe('mapFinding', () => {
  it('maps backend fields to the frontend Finding shape', () => {
    const f = mapFinding(
      {
        module: 'CORS',
        name: 'cors_wildcard',
        severity: 'critical',
        description: 'd',
        remediation: 'r',
        url: 'https://example.com',
      },
      3,
    )
    expect(f).toEqual({
      id: 'cors-3',
      module: 'cors',
      severity: 'critical',
      title: 'cors_wildcard',
      description: 'd',
      remediation: 'r',
      snippet: undefined,
      evidence: 'https://example.com',
    })
  })

  it('leaves evidence undefined when the backend sends no url', () => {
    const f = mapFinding(
      { module: 'headers', name: 'x', severity: 'low', description: '', remediation: '', url: null },
      0,
    )
    expect(f.evidence).toBeUndefined()
  })
})

describe('extractSnippet', () => {
  it('extracts the header line from a header remediation', () => {
    expect(extractSnippet('Thêm header: X-Frame-Options: DENY')).toBe('X-Frame-Options: DENY')
    expect(
      extractSnippet("Thêm header: Content-Security-Policy: default-src 'self'; script-src 'self';"),
    ).toBe("Content-Security-Policy: default-src 'self'; script-src 'self';")
  })

  it('extracts the flag from a cookie remediation', () => {
    expect(extractSnippet('Thêm cookie flag: SameSite=Lax hoặc Strict')).toBe(
      'SameSite=Lax hoặc Strict',
    )
  })

  it('returns undefined when the remediation carries no snippet', () => {
    expect(extractSnippet('Gia hạn chứng chỉ SSL ngay lập tức')).toBeUndefined()
  })

  it('is applied by mapFinding', () => {
    const f = mapFinding(
      {
        module: 'headers',
        name: 'x-frame-options',
        severity: 'medium',
        description: '',
        remediation: 'Thêm header: X-Frame-Options: DENY',
      },
      0,
    )
    expect(f.snippet).toBe('X-Frame-Options: DENY')
  })
})

describe('summarize', () => {
  it('counts findings per severity', () => {
    const summary = summarize([
      makeFinding({ severity: 'high' }),
      makeFinding({ severity: 'high' }),
      makeFinding({ severity: 'low' }),
    ])
    expect(summary).toEqual({ critical: 0, high: 2, medium: 0, low: 1, info: 0, total: 3 })
  })
})

describe('mapScanDetail', () => {
  it('builds a complete ScanResult with UTC dates and duration', () => {
    const result = mapScanDetail(makeApiScanDetail())
    expect(result.scan_id).toBe('abc12345-0000-0000-0000-000000000000')
    expect(result.url).toBe('https://example.com')
    expect(result.grade).toBe('A')
    expect(result.score).toBe(90)
    expect(result.started_at).toBe('2026-10-01T03:05:08.191297Z')
    expect(result.duration_ms).toBe(2434)
    expect(result.summary.high).toBe(1)
    expect(result.findings[0].module).toBe('cors')
  })

  it('keeps the scan mode reported by the backend', () => {
    expect(mapScanDetail(makeApiScanDetail({ mode: 'quick' })).mode).toBe('quick')
  })

  it('handles a scan without scoring or completion time', () => {
    const result = mapScanDetail(
      makeApiScanDetail({ scoring: null, completed_at: null, status: 'running', findings: [] }),
    )
    expect(result.grade).toBe('F')
    expect(result.score).toBe(0)
    expect(result.completed_at).toBeUndefined()
    expect(result.duration_ms).toBeUndefined()
  })
})

describe('mapHistoryItem', () => {
  it('converts seconds to milliseconds and renames fields', () => {
    const item = mapHistoryItem({
      id: 'id-1',
      target_url: 'https://example.com',
      mode: 'quick',
      status: 'completed',
      score: 46,
      grade: 'F',
      total_findings: 10,
      created_at: '2026-10-01T03:05:08',
      completed_at: '2026-10-01T03:05:10',
      duration_seconds: 2.43,
    })
    expect(item).toMatchObject({
      scan_id: 'id-1',
      url: 'https://example.com',
      mode: 'quick',
      status: 'completed',
      score: 46,
      grade: 'F',
      findings_count: 10,
      started_at: '2026-10-01T03:05:08Z',
      duration_ms: 2430,
    })
  })

  it('keeps null grade and score for scans that never completed', () => {
    const item = mapHistoryItem({
      id: 'id-2',
      target_url: 'https://example.com',
      mode: 'full',
      status: 'failed',
      score: null,
      grade: null,
      total_findings: 0,
      created_at: '2026-10-01T03:05:08',
      completed_at: null,
      duration_seconds: null,
    })
    expect(item.status).toBe('failed')
    expect(item.score).toBeNull()
    expect(item.grade).toBeNull()
    expect(item.duration_ms).toBeUndefined()
  })
})
