import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ScanPage from './ScanPage'
import AboutPage from './AboutPage'

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
