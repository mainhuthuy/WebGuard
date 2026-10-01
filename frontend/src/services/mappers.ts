/* ============================================================
   Mappers — backend DTOs → frontend domain types
   ============================================================ */

import type {
  ApiFinding,
  ApiHistoryItem,
  ApiScanDetail,
  Finding,
  Grade,
  ModuleName,
  ScanHistoryItem,
  ScanResult,
  Severity,
} from '../types'

const GRADES: Grade[] = ['A+', 'A', 'B', 'C', 'F']
const MODULES: ModuleName[] = ['headers', 'cookies', 'ssl_tls', 'information', 'cors']

/** Backend datetimes are naive UTC (no offset); make them explicit so Date parses them as UTC */
export function toUtcIso(value: string): string
export function toUtcIso(value: string | null | undefined): string | undefined
export function toUtcIso(value: string | null | undefined): string | undefined {
  if (!value) return undefined
  return /(Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`
}

/** Backend may return grades outside the UI scale (e.g. "D"); fall back to F */
export function toGrade(value: string | null | undefined): Grade {
  return GRADES.includes(value as Grade) ? (value as Grade) : 'F'
}

/** Backend module names are not normalised (e.g. "CORS") */
export function toModuleName(value: string | null | undefined): ModuleName {
  const lower = (value ?? '').toLowerCase()
  return MODULES.includes(lower as ModuleName) ? (lower as ModuleName) : 'information'
}

/**
 * Backend remediation texts embed the fix after a marker, e.g.
 * "Thêm header: X-Frame-Options: DENY" or "Thêm cookie flag: Secure".
 * Extract it so the UI can show a copyable snippet.
 */
export function extractSnippet(remediation: string): string | undefined {
  const match = remediation.match(/(?:Thêm header|Thêm cookie flag):\s*(.+)$/s)
  return match ? match[1].trim() : undefined
}

export function mapFinding(f: ApiFinding, index: number): Finding {
  const module = toModuleName(f.module)
  return {
    id: `${module}-${index}`,
    module,
    severity: f.severity,
    title: f.name,
    description: f.description,
    remediation: f.remediation,
    snippet: extractSnippet(f.remediation),
    evidence: f.url ?? undefined,
  }
}

export function summarize(findings: Finding[]): ScanResult['summary'] {
  const count = (s: Severity) => findings.filter((f) => f.severity === s).length
  return {
    critical: count('critical'),
    high: count('high'),
    medium: count('medium'),
    low: count('low'),
    info: count('info'),
    total: findings.length,
  }
}

export function mapScanDetail(d: ApiScanDetail): ScanResult {
  const findings = d.findings.map(mapFinding)
  const startedAt = toUtcIso(d.created_at)
  const completedAt = toUtcIso(d.completed_at)
  const durationMs = completedAt
    ? new Date(completedAt).getTime() - new Date(startedAt).getTime()
    : undefined
  return {
    scan_id: d.scan_id,
    url: d.target_url,
    mode: d.mode,
    status: d.status,
    grade: toGrade(d.scoring?.grade),
    score: d.scoring?.score ?? 0,
    findings,
    summary: summarize(findings),
    started_at: startedAt,
    completed_at: completedAt,
    duration_ms: durationMs,
  }
}

export function mapHistoryItem(h: ApiHistoryItem): ScanHistoryItem {
  return {
    scan_id: h.id,
    url: h.target_url,
    mode: h.mode,
    status: h.status,
    // Only completed scans have a meaningful grade/score
    grade: h.grade ? toGrade(h.grade) : null,
    score: h.score,
    findings_count: h.total_findings,
    started_at: toUtcIso(h.created_at),
    duration_ms: h.duration_seconds != null ? Math.round(h.duration_seconds * 1000) : undefined,
  }
}
