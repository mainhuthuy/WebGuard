import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SettingsPage from './SettingsPage'
import { getAISettings, saveAISettings } from '../utils/aiSettings'

beforeEach(() => {
  localStorage.clear()
})

describe('SettingsPage (AI BYOK settings)', () => {
  it('defaults to Google Gemini with an empty key', () => {
    render(<SettingsPage />)
    expect(screen.getByRole('button', { name: /Google Gemini/i })).toHaveClass(
      'ai-provider-option--active',
    )
    expect(screen.getByLabelText('API key')).toHaveValue('')
  })

  it('rejects an obviously too-short key instead of saving it', () => {
    render(<SettingsPage />)
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'abc' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText(/valid-looking API key/i)).toBeInTheDocument()
    expect(getAISettings()).toBeNull()
  })

  it('saves the chosen provider, key and model to this browser only', () => {
    render(<SettingsPage />)
    fireEvent.click(screen.getByRole('button', { name: /Groq/i }))
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'gsk_fake_key_12345' } })
    fireEvent.change(screen.getByLabelText(/Model/), { target: { value: 'llama-3.1-70b' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText(/Saved to this browser/i)).toBeInTheDocument()
    expect(getAISettings()).toEqual({
      provider: 'groq',
      apiKey: 'gsk_fake_key_12345',
      model: 'llama-3.1-70b',
    })
  })

  it('loads a previously saved key and offers to clear it', () => {
    saveAISettings({ provider: 'anthropic', apiKey: 'sk-ant-fake', model: 'claude-3-5-haiku-latest' })
    render(<SettingsPage />)

    expect(screen.getByLabelText('API key')).toHaveValue('sk-ant-fake')
    fireEvent.click(screen.getByRole('button', { name: /Clear saved key/i }))

    expect(getAISettings()).toBeNull()
    expect(screen.getByLabelText('API key')).toHaveValue('')
  })

  it('masks the API key by default and can reveal it', () => {
    render(<SettingsPage />)
    const input = screen.getByLabelText('API key') as HTMLInputElement
    expect(input.type).toBe('password')
    fireEvent.click(screen.getByRole('button', { name: 'Show API key' }))
    expect(input.type).toBe('text')
  })
})
