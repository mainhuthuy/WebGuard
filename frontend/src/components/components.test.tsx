import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Button, Badge, Card, Modal } from './common'
import ScoreCard from './results/ScoreCard'
import FindingDetail from './results/FindingDetail'
import ScanProgress from './scanner/ScanProgress'
import SeverityChart from './results/SeverityChart'
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

describe('SeverityChart', () => {
  const summary = { critical: 1, high: 2, medium: 3, low: 4, info: 0, total: 10 }

  it('fills the whole severity bar even when the summary also carries a total', () => {
    const { container } = render(<SeverityChart summary={summary} showChart={false} />)
    const widths = Array.from(container.querySelectorAll<HTMLElement>('.severity-bar__segment')).map(
      (el) => parseFloat(el.style.width),
    )
    expect(widths).toHaveLength(4) // the zero-count "info" segment is skipped
    expect(widths.reduce((a, b) => a + b, 0)).toBeCloseTo(100)
    expect(widths[0]).toBeCloseTo(10) // critical: 1 of 10
  })

  it('lists a count for every severity in the legend', () => {
    render(<SeverityChart summary={summary} showChart={false} />)
    expect(screen.getByText('Critical').nextElementSibling).toHaveTextContent('1')
    expect(screen.getByText('Low').nextElementSibling).toHaveTextContent('4')
    expect(screen.getByText('Informational').nextElementSibling).toHaveTextContent('0')
  })

  it('draws no bar when there are no findings', () => {
    const empty = { critical: 0, high: 0, medium: 0, low: 0, info: 0, total: 0 }
    const { container } = render(<SeverityChart summary={empty} showChart={false} />)
    expect(container.querySelector('.severity-bar')).toBeNull()
  })
})

describe('Modal', () => {
  it('renders into <body>, so a transformed ancestor cannot shift its fixed overlay', () => {
    render(
      <div style={{ transform: 'translateY(0)' }} data-testid="transformed-page">
        <Modal open onClose={vi.fn()} title="Details">
          Body text
        </Modal>
      </div>,
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog.parentElement).toBe(document.body)
    expect(screen.getByTestId('transformed-page')).not.toContainElement(dialog)
    expect(screen.getByText('Body text')).toBeInTheDocument()
  })

  it('renders nothing while closed', () => {
    render(
      <Modal open={false} onClose={vi.fn()}>
        Hidden
      </Modal>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('calls onClose when the overlay (but not the panel) is clicked', async () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} title="T">
        Inside
      </Modal>,
    )
    fireEvent.click(screen.getByText('Inside'))
    expect(onClose).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('dialog'))
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1))
  })
})
