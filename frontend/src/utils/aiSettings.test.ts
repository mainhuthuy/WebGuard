import { describe, it, expect, beforeEach, vi } from 'vitest'
import { getAISettings, saveAISettings, clearAISettings } from './aiSettings'

beforeEach(() => {
  localStorage.clear()
})

describe('aiSettings (BYOK, browser-local only)', () => {
  it('returns null when nothing has been saved', () => {
    expect(getAISettings()).toBeNull()
  })

  it('saves and reads back provider, key and optional model', () => {
    saveAISettings({ provider: 'google', apiKey: 'abc123', model: 'gemini-2.0-flash' })
    expect(getAISettings()).toEqual({ provider: 'google', apiKey: 'abc123', model: 'gemini-2.0-flash' })
  })

  it('omits model when not provided', () => {
    saveAISettings({ provider: 'groq', apiKey: 'abc123' })
    expect(getAISettings()).toEqual({ provider: 'groq', apiKey: 'abc123', model: undefined })
  })

  it('clears saved settings', () => {
    saveAISettings({ provider: 'openai', apiKey: 'abc123' })
    clearAISettings()
    expect(getAISettings()).toBeNull()
  })

  it('treats corrupted JSON as "nothing saved"', () => {
    localStorage.setItem('webguard:ai-settings', '{not json')
    expect(getAISettings()).toBeNull()
  })

  it('treats a saved value missing the key as "nothing saved"', () => {
    localStorage.setItem('webguard:ai-settings', JSON.stringify({ provider: 'google' }))
    expect(getAISettings()).toBeNull()
  })

  it('never throws when localStorage access fails (private mode / blocked storage)', () => {
    const getSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const setSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const removeSpy = vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('blocked')
    })

    expect(getAISettings()).toBeNull()
    expect(saveAISettings({ provider: 'google', apiKey: 'x' })).toBe(false)
    expect(() => clearAISettings()).not.toThrow()

    getSpy.mockRestore()
    setSpy.mockRestore()
    removeSpy.mockRestore()
  })
})
