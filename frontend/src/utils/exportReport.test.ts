import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { exportAsJson, exportAsHtml } from './exportReport'
import { makeResult, makeFinding } from '../test/fixtures'

/** jsdom's Blob has no .text(); read it through FileReader */
function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}

let blobs: Blob[]
let clicked: { download: string }[]

beforeEach(() => {
  blobs = []
  clicked = []
  URL.createObjectURL = vi.fn((b: Blob | MediaSource) => {
    blobs.push(b as Blob)
    return 'blob:mock'
  })
  URL.revokeObjectURL = vi.fn()
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    clicked.push({ download: this.download })
  })
})

afterEach(async () => {
  vi.useRealTimers()
  // Let the download helper's 100ms cleanup timer run before the next test
  await new Promise((r) => setTimeout(r, 120))
  vi.restoreAllMocks()
})

describe('exportAsJson', () => {
  it('downloads the result as pretty JSON with a hostname-based filename', async () => {
    const result = makeResult()
    exportAsJson(result)

    expect(clicked).toHaveLength(1)
    expect(clicked[0].download).toBe(`webguard_example.com_${result.scan_id}.json`)
    expect(blobs[0].type).toContain('application/json')
    expect(JSON.parse(await readBlob(blobs[0]))).toEqual(result)
  })

  it('cleans up the object URL and anchor afterwards', () => {
    vi.useFakeTimers() // FileReader needs real timers, so only fake them here
    exportAsJson(makeResult())
    vi.advanceTimersByTime(150)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock')
    expect(document.querySelectorAll('a[download]')).toHaveLength(0)
  })
})

describe('exportAsHtml', () => {
  it('produces a standalone HTML report with grade, score and findings', async () => {
    exportAsHtml(makeResult())
    const html = await readBlob(blobs[0])

    expect(clicked[0].download.endsWith('.html')).toBe(true)
    expect(html).toContain('<!DOCTYPE html>')
    expect(html).toContain('78 / 100')
    expect(html).toContain('Missing Content-Security-Policy')
  })

  it('escapes HTML in user-controlled fields', async () => {
    const result = makeResult({
      url: 'https://example.com/?q=<script>alert(1)</script>',
      findings: [makeFinding({ title: '<img src=x onerror=alert(1)>' })],
    })
    exportAsHtml(result)
    const html = await readBlob(blobs[0])

    expect(html).not.toContain('<script>alert(1)</script>')
    expect(html).not.toContain('<img src=x onerror=alert(1)>')
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;')
  })

  it('shows a friendly message when there are no findings', async () => {
    exportAsHtml(
      makeResult({
        findings: [],
        summary: { critical: 0, high: 0, medium: 0, low: 0, info: 0, total: 0 },
      }),
    )
    expect(await readBlob(blobs[0])).toContain('No security issues detected')
  })
})
