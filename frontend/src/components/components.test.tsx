import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Button, Badge, Card } from './common'
import ScoreCard from './results/ScoreCard'
import FindingDetail from './results/FindingDetail'
import ScanProgress from './scanner/ScanProgress'
import { makeFinding } from '../test/fixtures'

describe('Button', () => {
  it('fires onClick', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Scan</Button>)
    fireEvent.click(screen.getByRole('button', { name: 'Scan' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled and does not fire while loading', () => {
    const onClick = vi.fn()
    render(
      <Button loading onClick={onClick}>
        Scanning
      </Button>,
    )
    const btn = screen.getByRole('button', { name: /scanning/i })
    expect(btn).toBeDisabled()
    fireEvent.click(btn)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('applies variant and size classes', () => {
    render(
      <Button variant="danger" size="sm">
        Delete
      </Button>,
    )
    const btn = screen.getByRole('button', { name: 'Delete' })
    expect(btn).toHaveClass('btn--danger', 'btn--sm')
  })
})

describe('Badge', () => {
  it('renders its label with the severity variant', () => {
    render(<Badge variant="critical">Critical</Badge>)
    expect(screen.getByText('Critical')).toHaveClass('badge--critical')
  })
})

describe('Card', () => {
  it('renders header, body and footer', () => {
    render(
      <Card header="Head" footer="Foot">
        Body
      </Card>,
    )
    expect(screen.getByText('Head')).toBeInTheDocument()
    expect(screen.getByText('Body')).toBeInTheDocument()
    expect(screen.getByText('Foot')).toBeInTheDocument()
  })
})

describe('ScoreCard', () => {
  it('shows grade, score and target URL', () => {
    render(<ScoreCard grade="B" score={78} url="https://example.com" />)
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText(/78/)).toBeInTheDocument()
    expect(screen.getByText('https://example.com')).toBeInTheDocument()
  })

  it('formats duration in ms and seconds', () => {
    const { rerender } = render(
      <ScoreCard grade="A" score={90} url="https://example.com" duration={450} />,
    )
    expect(screen.getByText('450ms')).toBeInTheDocument()
    rerender(<ScoreCard grade="A" score={90} url="https://example.com" duration={2400} />)
    expect(screen.getByText('2.4s')).toBeInTheDocument()
  })

  it('omits duration when not provided', () => {
    render(<ScoreCard grade="F" score={10} url="https://example.com" />)
    expect(screen.queryByText(/\d+(ms|\.\ds)$/)).not.toBeInTheDocument()
  })

  it('applies the grade class', () => {
    const { container } = render(<ScoreCard grade="A+" score={99} url="https://example.com" />)
    expect(container.firstElementChild).toHaveClass('score-card--a-plus')
  })
})

describe('FindingDetail', () => {
  it('renders description and remediation', () => {
    render(<FindingDetail finding={makeFinding()} />)
    expect(screen.getByText('No CSP header was detected.')).toBeInTheDocument()
    expect(screen.getByText('Add a Content-Security-Policy header.')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('shows evidence and snippet only when present', () => {
    const { rerender } = render(<FindingDetail finding={makeFinding()} />)
    expect(screen.queryByText('Evidence')).not.toBeInTheDocument()
    expect(screen.queryByText('Recommended Fix')).not.toBeInTheDocument()

    rerender(
      <FindingDetail
        finding={makeFinding({ evidence: 'Header not present', snippet: 'X-Frame-Options: DENY' })}
      />,
    )
    expect(screen.getByText('Header not present')).toBeInTheDocument()
    expect(screen.getByText('X-Frame-Options: DENY')).toBeInTheDocument()
  })

  it('copies the snippet to the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })

    render(<FindingDetail finding={makeFinding({ snippet: 'X-Frame-Options: DENY' })} />)
    fireEvent.click(screen.getByTitle('Copy to clipboard'))

    expect(writeText).toHaveBeenCalledWith('X-Frame-Options: DENY')
    expect(await screen.findByText('Copied')).toBeInTheDocument()
  })
})

describe('ScanProgress — failure state', () => {
  const baseProps = { url: 'https://example.com', progress: 40, modules: [], logs: [] }

  it('shows the failure reason and a retry button', () => {
    const onRetry = vi.fn()
    render(
      <ScanProgress
        {...baseProps}
        completed
        errored
        errorMessage="Lost connection to the scan stream."
        onRetry={onRetry}
      />,
    )
    expect(screen.getByText('Scan Failed')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('Lost connection to the scan stream.')
    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('falls back to a generic message and does not offer results', () => {
    render(<ScanProgress {...baseProps} completed errored onViewResults={vi.fn()} />)
    expect(screen.getByRole('alert')).toHaveTextContent('could not be completed')
    expect(screen.queryByRole('button', { name: /view results/i })).not.toBeInTheDocument()
  })

  it('shows no failure UI for a successful scan', () => {
    render(<ScanProgress {...baseProps} progress={100} completed onViewResults={vi.fn()} />)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view results/i })).toBeInTheDocument()
  })
})
