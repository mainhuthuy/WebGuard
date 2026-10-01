/* ============================================================
   WebGuard Frontend Type Definitions
   Mirrors backend Pydantic schemas for type safety.
   ============================================================ */

/** Severity levels for findings */
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** Security grade scale */
export type Grade = 'A+' | 'A' | 'B' | 'C' | 'F'

/** Scan mode: quick (headers+ssl only) or full (all modules) */
export type ScanMode = 'quick' | 'full'

/** Scan lifecycle status */
export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

/** Individual module names */
export type ModuleName = 'headers' | 'cookies' | 'ssl_tls' | 'information' | 'cors'

/** Request to initiate a scan */
export interface ScanRequest {
  url: string
  mode: ScanMode
}

/** A single finding from a scan module */
export interface Finding {
  id: string
  module: ModuleName
  severity: Severity
  title: string
  description: string
  remediation: string
  /** Optional code snippet showing the fix */
  snippet?: string
  /** Raw evidence (e.g., the header value found) */
  evidence?: string
}

/** Progress update from SSE stream */
export interface ScanProgress {
  scan_id: string
  status: ScanStatus
  current_module?: ModuleName
  module_index?: number
  total_modules: number
  percentage: number
  message: string
  timestamp: string
}

/** Complete scan result */
export interface ScanResult {
  scan_id: string
  url: string
  mode: ScanMode
  status: ScanStatus
  grade: Grade
  score: number
  findings: Finding[]
  summary: {
    critical: number
    high: number
    medium: number
    low: number
    info: number
    total: number
  }
  started_at: string
  completed_at?: string
  duration_ms?: number
}

/** Scan history list item (lightweight) */
export interface ScanHistoryItem {
  scan_id: string
  url: string
  mode: ScanMode
  grade: Grade
  score: number
  findings_count: number
  started_at: string
  duration_ms?: number
}
