/* ============================================================
   Backend DTOs — mirrors backend/app/schemas/*.py (snake_case, raw)
   ============================================================ */

import type { AIProvider, ScanMode, ScanStatus } from './scan'

export interface ApiFinding {
  module: string
  name: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  description: string
  remediation: string
  url?: string | null
}

export interface ApiScoring {
  score: number
  grade: string
  total_findings: number
}

export interface ApiScanCreateResponse {
  scan_id: string
  target_url: string
  mode: ScanMode
  status: ScanStatus
  created_at: string
}

export interface ApiScanDetail {
  scan_id: string
  target_url: string
  mode: ScanMode
  status: ScanStatus
  created_at: string
  completed_at: string | null
  total_findings: number
  findings: ApiFinding[]
  scoring: ApiScoring | null
}

export interface ApiScanCancelResponse {
  scan_id: string
  status: ScanStatus
  message: string
}

export interface ApiHistoryItem {
  id: string
  target_url: string
  mode: ScanMode
  status: ScanStatus
  score: number | null
  grade: string | null
  total_findings: number
  created_at: string
  completed_at: string | null
  duration_seconds: number | null
}

export interface ApiHistoryPage {
  items: ApiHistoryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ApiHistoryStats {
  total_scans: number
  completed_scans: number
  failed_scans: number
  cancelled_scans: number
  average_score: number | null
  grade_distribution: Record<string, number>
}

export interface ApiDeleteResponse {
  deleted: boolean
  message: string
  deleted_count: number
}

/** POST /scan/{id}/explain — request body (api_key is the user's own, forwarded once, never stored) */
export interface ApiExplainRequest {
  provider: AIProvider
  api_key: string
  model?: string
}

export interface ApiExplainResponse {
  provider: AIProvider
  model: string
  explanation: string
}

/** Query params of GET /history */
export interface HistoryQuery {
  page?: number
  page_size?: number
  search_url?: string
  status?: ScanStatus
  grade?: string
  sort_by?: 'created_at' | 'score'
  sort_order?: 'asc' | 'desc'
  from_date?: string
  to_date?: string
}
