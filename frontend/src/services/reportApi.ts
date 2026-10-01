/* ============================================================
   reportApi — /report endpoints
   ============================================================ */

import { apiClient } from './apiClient'

export type ReportFormat = 'json' | 'html'

export const reportApi = {
  /** GET /report/{id}/export?format= — returns the file as a Blob */
  async exportReport(scanId: string, format: ReportFormat): Promise<Blob> {
    const { data } = await apiClient.get<Blob>(
      `/report/${encodeURIComponent(scanId)}/export`,
      { params: { format }, responseType: 'blob' },
    )
    return data
  },

  /** Filename matching the backend: webguard_report_<first 8 chars>.<ext> */
  filename(scanId: string, format: ReportFormat): string {
    return `webguard_report_${scanId.slice(0, 8)}.${format}`
  },
}
