/* ============================================================
   AI settings (BYOK) — stored ONLY in this browser's localStorage.

   The API key never touches our backend's database: it is read from here and
   sent once per "Explain with AI" request, forwarded straight to the chosen
   provider, then discarded server-side. Clearing browser storage or using a
   different browser/device means pasting the key again.
   ============================================================ */

import type { AISettings } from '../types'

const STORAGE_KEY = 'webguard:ai-settings'

/** Read saved AI settings, or null if none saved / storage unavailable / corrupted. */
export function getAISettings(): AISettings | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<AISettings>
    if (!parsed.provider || !parsed.apiKey) return null
    return { provider: parsed.provider, apiKey: parsed.apiKey, model: parsed.model }
  } catch {
    return null
  }
}

/** Save AI settings to this browser only. Returns false if storage is unavailable. */
export function saveAISettings(settings: AISettings): boolean {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    return true
  } catch {
    return false
  }
}

/** Remove saved AI settings from this browser. */
export function clearAISettings(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage unavailable (private mode, blocked) — nothing to clear anyway.
  }
}
