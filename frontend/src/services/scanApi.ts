/* ============================================================
   scanApi — /scan and /history endpoints
   ============================================================ */

import { apiClient } from './apiClient'
import { API_BASE_URL } from '../config'
import type {
  ApiDeleteResponse,
  ApiExplainRequest,
  ApiExplainResponse,
  ApiHistoryPage,
  ApiHistoryStats,
  ApiScanCancelResponse,
  ApiScanCreateResponse,
  ApiScanDetail,
  HistoryQuery,
  ScanMode,
} from '../types'

export const scanApi = {
  /** POST /scan — create a pending scan (quick | full), returns its id */
  async createScan(url: string, mode: ScanMode = 'full'): Promise<ApiScanCreateResponse> {
    const { data } = await apiClient.post<ApiScanCreateResponse>('/scan', { url, mode })
    return data
  },

  /** GET /scan/{id} */
  async getScan(scanId: string): Promise<ApiScanDetail> {
    const { data } = await apiClient.get<ApiScanDetail>(`/scan/${encodeURIComponent(scanId)}`)
    return data
  },

  /** POST /scan/{id}/cancel */
  async cancelScan(scanId: string): Promise<ApiScanCancelResponse> {
    const { data } = await apiClient.post<ApiScanCancelResponse>(
      `/scan/${encodeURIComponent(scanId)}/cancel`,
    )
    return data
  },

  /**
   * POST /scan/{id}/explain — ask an AI provider (BYOK: the user's own API key) to explain the
   * findings and suggest a detailed remediation plan. The request body carries the user's own
   * key straight through to our backend, which forwards it once to the provider and never stores
   * it. No new requests are sent to the scanned target by this call.
   */
  async explainScan(scanId: string, body: ApiExplainRequest): Promise<ApiExplainResponse> {
    const { data } = await apiClient.post<ApiExplainResponse>(
      `/scan/${encodeURIComponent(scanId)}/explain`,
      body,
    )
    return data
  },

  /** URL for the SSE stream (consumed by EventSource, not axios) */
  streamUrl(scanId: string): string {
    return `${API_BASE_URL}/scan/${encodeURIComponent(scanId)}/stream`
  },

  /** GET /history */
  async getHistory(query: HistoryQuery = {}): Promise<ApiHistoryPage> {
    const { data } = await apiClient.get<ApiHistoryPage>('/history', { params: query })
    return data
  },

  /** GET /history/stats */
  async getHistoryStats(): Promise<ApiHistoryStats> {
    const { data } = await apiClient.get<ApiHistoryStats>('/history/stats')
    return data
  },

  /** DELETE /history/{id} */
  async deleteScan(scanId: string): Promise<ApiDeleteResponse> {
    const { data } = await apiClient.delete<ApiDeleteResponse>(
      `/history/${encodeURIComponent(scanId)}`,
    )
    return data
  },
}
