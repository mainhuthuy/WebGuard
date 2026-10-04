import type { ApiScanDetail, Finding, ScanResult } from '../types'

export function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 'headers-0',
    module: 'headers',
    severity: 'high',
    title: 'Missing Content-Security-Policy',
    description: 'No CSP header was detected.',
    remediation: 'Add a Content-Security-Policy header.',
    ...overrides,
  }
}

export function makeResult(overrides: Partial<ScanResult> = {}): ScanResult {
  const findings = [makeFinding(), makeFinding({ id: 'cors-1', module: 'cors', severity: 'low' })]
  return {
    scan_id: '244fc8c3-83a4-42c8-9568-9ed64e66d903',
    url: 'https://example.com',
    mode: 'full',
    status: 'completed',
    grade: 'B',
    score: 78,
    findings,
    summary: { critical: 0, high: 1, medium: 0, low: 1, info: 0, total: 2 },
    started_at: '2026-10-01T03:05:08.000Z',
    completed_at: '2026-10-01T03:05:10.000Z',
    duration_ms: 2000,
    ...overrides,
  }
}

export function makeApiScanDetail(overrides: Partial<ApiScanDetail> = {}): ApiScanDetail {
  return {
    scan_id: 'abc12345-0000-0000-0000-000000000000',
    target_url: 'https://example.com',
    mode: 'full',
    status: 'completed',
    created_at: '2026-10-01T03:05:08.191297',
    completed_at: '2026-10-01T03:05:10.625503',
    total_findings: 1,
    findings: [
      {
        module: 'CORS',
        name: 'cors_wildcard',
        severity: 'high',
        description: 'Wildcard origin',
        remediation: 'Use an allowlist',
        url: 'https://example.com',
      },
    ],
    scoring: { score: 90, grade: 'A', total_findings: 1 },
    ...overrides,
  }
}
