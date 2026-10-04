import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'
import ScanPage from './ScanPage'
import AboutPage from './AboutPage'
import { CHECK_MODULES, SEVERITY_GUIDE, TOTAL_CHECKS } from './aboutChecks'

describe('ScanPage', () => {
  function setup(props: Parameters<typeof ScanPage>[0] = {}) {
    const onStartScan = vi.fn()
    render(<ScanPage onStartScan={onStartScan} {...props} />)
    const input = screen.getByPlaceholderText('https://example.com')
    return { onStartScan, input }
  }

  it('shows an error and does not scan when the URL is empty', () => {
    const { onStartScan } = setup()
    fireEvent.click(screen.getByRole('button', { name: /scan target/i }))
    expect(screen.getByText('Please enter a target URL.')).toBeInTheDocument()
    expect(onStartScan).not.toHaveBeenCalled()
  })

  it('prepends https:// when the protocol is missing', () => {
    const { onStartScan, input } = setup()
    fireEvent.change(input, { target: { value: 'example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /scan target/i }))
    expect(onStartScan).toHaveBeenCalledWith('https://example.com', 'full')
  })

  it('rejects an invalid URL', () => {
    const { onStartScan, input } = setup()
    fireEvent.change(input, { target: { value: 'http://' } })
    fireEvent.click(screen.getByRole('button', { name: /scan target/i }))
    expect(screen.getByText(/valid URL/i)).toBeInTheDocument()
    expect(onStartScan).not.toHaveBeenCalled()
  })

  it('passes the selected scan mode', () => {
    const { onStartScan, input } = setup()
    fireEvent.click(screen.getByText('Quick Scan'))
    fireEvent.change(input, { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /scan target/i }))
    expect(onStartScan).toHaveBeenCalledWith('https://example.com', 'quick')
  })

  it('clears the error as soon as the user types', () => {
    const { input } = setup()
    fireEvent.click(screen.getByRole('button', { name: /scan target/i }))
    expect(screen.getByText('Please enter a target URL.')).toBeInTheDocument()
    fireEvent.change(input, { target: { value: 'a' } })
    expect(screen.queryByText('Please enter a target URL.')).not.toBeInTheDocument()
  })

  it('disables the form while scanning', () => {
    const { input } = setup({ scanning: true })
    expect(input).toBeDisabled()
    expect(screen.getByRole('button', { name: /scanning/i })).toBeDisabled()
  })
})

describe('AboutPage', () => {
  it('renders the scoring reference matching the backend engine', () => {
    render(<AboutPage />)
    expect(screen.getByText('−15')).toBeInTheDocument() // critical
    expect(screen.getByText('95 – 100')).toBeInTheDocument() // A+
  })

  it('shows the authorized-use disclaimer', () => {
    render(<AboutPage />)
    expect(screen.getByText('Authorized use only')).toBeInTheDocument()
    expect(screen.getByText('No warranty')).toBeInTheDocument()
  })

  it('shows the start button only when a handler is given', () => {
    const { rerender } = render(<AboutPage />)
    expect(screen.queryByRole('button', { name: /start a scan/i })).not.toBeInTheDocument()

    const onStartScan = vi.fn()
    rerender(<AboutPage onStartScan={onStartScan} />)
    fireEvent.click(screen.getByRole('button', { name: /start a scan/i }))
    expect(onStartScan).toHaveBeenCalledTimes(1)
  })
})

describe('AboutPage — what the tool checks', () => {
  it('lists every module with all of its checks and their risk', () => {
    render(<AboutPage />)
    for (const m of CHECK_MODULES) {
      const card = document.getElementById(`about-module-${m.id}`) as HTMLElement
      expect(card).toBeInTheDocument()
      expect(within(card).getByText(m.title)).toBeInTheDocument()
      for (const c of m.checks) {
        expect(within(card).getByText(c.name)).toBeInTheDocument()
        expect(within(card).getByText(c.what)).toBeInTheDocument()
      }
      expect(within(card).getAllByText(/Risk:/)).toHaveLength(m.checks.length)
    }
  })

  it('states the total number of checks and which scan mode runs what', () => {
    render(<AboutPage />)
    expect(screen.getByText(new RegExp(`${TOTAL_CHECKS} checks across ${CHECK_MODULES.length} modules`))).toBeInTheDocument()
    expect(within(document.getElementById('about-module-headers') as HTMLElement).getByText(/Quick & Full scans/)).toBeInTheDocument()
    expect(within(document.getElementById('about-module-cors') as HTMLElement).getByText(/Full scans only/)).toBeInTheDocument()
  })

  it('explains each risk level with its score penalty', () => {
    render(<AboutPage />)
    for (const s of SEVERITY_GUIDE) {
      expect(screen.getByText(s.meaning)).toBeInTheDocument()
      expect(screen.getAllByText(`−${s.penalty} pts each`)).toHaveLength(1)
    }
  })

  it('only uses the severities the backend can produce, and every check is documented', () => {
    for (const m of CHECK_MODULES) {
      for (const c of m.checks) {
        expect(['critical', 'high', 'medium', 'low']).toContain(c.severity)
        expect(c.what.length).toBeGreaterThan(10)
        expect(c.risk.length).toBeGreaterThan(10)
      }
    }
    // quick scans = headers + ssl_tls only (must match backend Scanner)
    const quick = CHECK_MODULES.filter((m) => m.modes.includes('quick')).map((m) => m.id)
    expect(quick).toEqual(['headers', 'ssl_tls'])
  })
})
