/* ============================================================
   useReport — Report export hook
   Wraps client-side JSON/HTML export with status tracking.
   Server-side export via /api/v1/report is wired in task 3.11.
   ============================================================ */

import { useState, useCallback } from 'react'
import { exportAsJson, exportAsHtml } from '../utils/exportReport'
import type { ScanResult } from '../types'

export type ReportFormat = 'json' | 'html'

export interface UseReportReturn {
  /** Format currently being exported (null when idle) */
  exporting: ReportFormat | null
  /** Last export error message, if any */
  error: string | null
  /** Export the given result in the chosen format. Returns true on success. */
  exportReport: (result: ScanResult, format: ReportFormat) => boolean
  /** Clear the last error */
  clearError: () => void
}

export function useReport(): UseReportReturn {
  const [exporting, setExporting] = useState<ReportFormat | null>(null)
  const [error, setError] = useState<string | null>(null)

  const exportReport = useCallback((result: ScanResult, format: ReportFormat) => {
    setError(null)
    setExporting(format)
    try {
      if (format === 'json') exportAsJson(result)
      else exportAsHtml(result)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export report')
      return false
    } finally {
      setExporting(null)
    }
  }, [])

  const clearError = useCallback(() => setError(null), [])

  return { exporting, error, exportReport, clearError }
}
