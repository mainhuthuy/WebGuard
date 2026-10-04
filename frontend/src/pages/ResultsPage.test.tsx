import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ResultsPage from './ResultsPage'
import { makeResult } from '../test/fixtures'
import { saveAISettings } from '../utils/aiSettings'
import { ApiError } from '../services'

const explainScan = vi.fn()

vi.mock('../services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services')>()
  return {
    ...actual,
    scanApi: { ...actual.scanApi, explainScan: (...a: unknown[]) => explainScan(...a) },
  }
})

beforeEach(() => {
  localStorage.clear()
  explainScan.mockReset()
})

describe('ResultsPage — Explain with AI (BYOK)', () => {
  it('prompts to set up AI Settings when no key is saved yet', () => {
    const onOpenAISettings = vi.fn()
    render(<ResultsPage result={makeResult()} onOpenAISettings={onOpenAISettings} />)

    expect(screen.getByText(/Get a detailed, AI-written remediation plan/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Set up AI Settings/i }))
    expect(onOpenAISettings).toHaveBeenCalledTimes(1)
    expect(explainScan).not.toHaveBeenCalled()
  })

  it('calls the explain endpoint with the saved key and shows the result', async () => {
    saveAISettings({ provider: 'google', apiKey: 'fake-key-123', model: 'gemini-2.0-flash' })
    explainScan.mockResolvedValue({
      provider: 'google',
      model: 'gemini-2.0-flash',
      explanation: '## Plan\nFix the CSP header first.',
    })

    const result = makeResult()
    render(<ResultsPage result={result} />)

    fireEvent.click(screen.getByRole('button', { name: /Explain with AI/i }))

    await waitFor(() => {
      expect(screen.getByText(/Fix the CSP header first/i)).toBeInTheDocument()
    })

    expect(explainScan).toHaveBeenCalledWith(result.scan_id, {
      provider: 'google',
      api_key: 'fake-key-123',
      model: 'gemini-2.0-flash',
    })
  })

  it('shows the provider error message when the call fails (e.g. bad key)', async () => {
    saveAISettings({ provider: 'openai', apiKey: 'bad-key' })
    explainScan.mockRejectedValue(new ApiError('API key bị OpenAI từ chối.', 401, 'HTTP_ERROR'))

    render(<ResultsPage result={makeResult()} />)
    fireEvent.click(screen.getByRole('button', { name: /Explain with AI/i }))

    await waitFor(() => {
      expect(screen.getByText(/API key bị OpenAI từ chối/i)).toBeInTheDocument()
    })
  })

  it('lets the user regenerate the explanation', async () => {
    saveAISettings({ provider: 'google', apiKey: 'fake-key-123' })
    explainScan.mockResolvedValue({ provider: 'google', model: 'gemini-2.0-flash', explanation: 'first answer' })

    render(<ResultsPage result={makeResult()} />)
    fireEvent.click(screen.getByRole('button', { name: /Explain with AI/i }))
    await waitFor(() => expect(screen.getByText('first answer')).toBeInTheDocument())

    explainScan.mockResolvedValue({ provider: 'google', model: 'gemini-2.0-flash', explanation: 'second answer' })
    fireEvent.click(screen.getByRole('button', { name: /Regenerate/i }))

    await waitFor(() => expect(screen.getByText('second answer')).toBeInTheDocument())
    expect(explainScan).toHaveBeenCalledTimes(2)
  })
})
