import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useReport } from './useReport'
import { makeResult } from '../test/fixtures'

const exportReportApi = vi.fn()
const exportAsJson = vi.fn()
const exportAsHtml = vi.fn()
const downloadBlob = vi.fn()

vi.mock('../services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services')>()
  return {
    ...actual,
    reportApi: {
      exportReport: (...args: unknown[]) => exportReportApi(...args),
      filename: actual.reportApi.filename,
    },
  }
})

vi.mock('../utils/exportReport', () => ({
  exportAsJson: (...args: unknown[]) => exportAsJson(...args),
  exportAsHtml: (...args: unknown[]) => exportAsHtml(...args),
  downloadBlob: (...args: unknown[]) => downloadBlob(...args),
}))

beforeEach(() => {
  vi.clearAllMocks()
  vi.spyOn(console, 'warn').mockImplementation(() => undefined)
})

describe('useReport', () => {
  it('downloads the server-generated report when available', async () => {
    const blob = new Blob(['{}'])
    exportReportApi.mockResolvedValue(blob)
    const { result } = renderHook(() => useReport({ clientOnly: false }))
    const scan = makeResult()

    let ok = false
    await act(async () => {
      ok = await result.current.exportReport(scan, 'json')
    })

    expect(ok).toBe(true)
    expect(exportReportApi).toHaveBeenCalledWith(scan.scan_id, 'json')
    expect(downloadBlob).toHaveBeenCalledWith(blob, 'webguard_report_244fc8c3.json')
    expect(exportAsJson).not.toHaveBeenCalled()
  })

  it('falls back to client-side export when the server fails', async () => {
    exportReportApi.mockRejectedValue(new Error('down'))
    const { result } = renderHook(() => useReport({ clientOnly: false }))
    const scan = makeResult()

    await act(async () => {
      await result.current.exportReport(scan, 'html')
    })

    expect(exportAsHtml).toHaveBeenCalledWith(scan)
    expect(downloadBlob).not.toHaveBeenCalled()
    expect(result.current.error).toBeNull()
  })

  it('skips the server entirely in client-only mode', async () => {
    const { result } = renderHook(() => useReport({ clientOnly: true }))
    const scan = makeResult()

    await act(async () => {
      await result.current.exportReport(scan, 'json')
    })

    expect(exportReportApi).not.toHaveBeenCalled()
    expect(exportAsJson).toHaveBeenCalledWith(scan)
  })

  it('reports an error when client-side export itself fails', async () => {
    exportAsJson.mockImplementation(() => {
      throw new Error('disk full')
    })
    const { result } = renderHook(() => useReport({ clientOnly: true }))

    let ok = true
    await act(async () => {
      ok = await result.current.exportReport(makeResult(), 'json')
    })

    expect(ok).toBe(false)
    expect(result.current.error).toBe('disk full')
    expect(result.current.exporting).toBeNull()

    act(() => result.current.clearError())
    expect(result.current.error).toBeNull()
  })
})
