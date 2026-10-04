import { useState, type FormEvent } from 'react'
import { Sparkles, Eye, EyeOff, ExternalLink, ShieldCheck, Trash2, CheckCircle2 } from 'lucide-react'
import { Button, Card, Badge } from '../components/common'
import { getAISettings, saveAISettings, clearAISettings } from '../utils/aiSettings'
import type { AIProvider } from '../types'
import './SettingsPage.css'

interface ProviderInfo {
  id: AIProvider
  name: string
  tierHint: string
  tierKind: 'free' | 'paid'
  keyUrl: string
  defaultModel: string
}

/** Mirrors backend/app/services/ai_explainer.py PROVIDERS (default models kept in sync) */
const PROVIDERS: ProviderInfo[] = [
  {
    id: 'google',
    name: 'Google Gemini',
    tierHint: 'Free tier (Google AI Studio)',
    tierKind: 'free',
    keyUrl: 'https://aistudio.google.com/apikey',
    defaultModel: 'gemini-2.0-flash',
  },
  {
    id: 'groq',
    name: 'Groq',
    tierHint: 'Generous free tier',
    tierKind: 'free',
    keyUrl: 'https://console.groq.com/keys',
    defaultModel: 'llama-3.1-8b-instant',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    tierHint: 'Several free models available',
    tierKind: 'free',
    keyUrl: 'https://openrouter.ai/keys',
    defaultModel: 'meta-llama/llama-3.1-8b-instruct:free',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    tierHint: 'Paid (small trial credit for new accounts)',
    tierKind: 'paid',
    keyUrl: 'https://platform.openai.com/api-keys',
    defaultModel: 'gpt-4o-mini',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    tierHint: 'Paid',
    tierKind: 'paid',
    keyUrl: 'https://console.anthropic.com/settings/keys',
    defaultModel: 'claude-3-5-haiku-latest',
  },
]

export default function SettingsPage() {
  const saved = getAISettings()
  const [provider, setProvider] = useState<AIProvider>(saved?.provider ?? 'google')
  const [apiKey, setApiKey] = useState(saved?.apiKey ?? '')
  const [model, setModel] = useState(saved?.model ?? '')
  const [showKey, setShowKey] = useState(false)
  const [status, setStatus] = useState<'idle' | 'saved' | 'cleared' | 'error'>('idle')

  const activeProvider = PROVIDERS.find((p) => p.id === provider)!

  const handleSave = (e: FormEvent) => {
    e.preventDefault()
    const trimmedKey = apiKey.trim()
    if (trimmedKey.length < 8) {
      setStatus('error')
      return
    }
    const ok = saveAISettings({ provider, apiKey: trimmedKey, model: model.trim() || undefined })
    setStatus(ok ? 'saved' : 'error')
  }

  const handleClear = () => {
    clearAISettings()
    setApiKey('')
    setModel('')
    setStatus('cleared')
  }

  return (
    <div className="settings-page">
      <div className="settings-page__header">
        <div className="settings-page__icon">
          <Sparkles size={28} />
        </div>
        <div>
          <h1 className="settings-page__title">AI Settings</h1>
          <p className="settings-page__subtitle">
            Bring your own API key to unlock <strong>“Explain with AI”</strong> on the results
            page — a plain-language risk summary and a detailed, prioritised remediation plan
            for the findings a scan already found.
          </p>
        </div>
      </div>

      <Card padding="spacious" className="settings-page__card">
        <h2 className="settings-page__section-title">1. Choose a provider</h2>
        <div className="ai-provider-grid">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              type="button"
              className={`ai-provider-option ${provider === p.id ? 'ai-provider-option--active' : ''}`}
              onClick={() => setProvider(p.id)}
              id={`ai-provider-${p.id}`}
            >
              <div className="ai-provider-option__top">
                <span className="ai-provider-option__name">{p.name}</span>
                <Badge variant={p.tierKind === 'free' ? 'success' : 'neutral'} size="sm">
                  {p.tierKind === 'free' ? 'Free tier' : 'Paid'}
                </Badge>
              </div>
              <span className="ai-provider-option__hint">{p.tierHint}</span>
            </button>
          ))}
        </div>

        <a
          href={activeProvider.keyUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="settings-page__key-link"
        >
          Get a {activeProvider.name} API key <ExternalLink size={14} />
        </a>

        <form onSubmit={handleSave} className="settings-form">
          <h2 className="settings-page__section-title">2. Paste your API key</h2>

          <div className="settings-form__field">
            <label htmlFor="ai-api-key" className="settings-form__label">
              API key
            </label>
            <div className="settings-form__input-row">
              <input
                id="ai-api-key"
                type={showKey ? 'text' : 'password'}
                className="settings-form__input"
                placeholder="Paste your key here"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  if (status !== 'idle') setStatus('idle')
                }}
                autoComplete="off"
                spellCheck={false}
              />
              <button
                type="button"
                className="settings-form__visibility"
                onClick={() => setShowKey((v) => !v)}
                aria-label={showKey ? 'Hide API key' : 'Show API key'}
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="settings-form__field">
            <label htmlFor="ai-model" className="settings-form__label">
              Model <span className="settings-form__label-optional">(optional)</span>
            </label>
            <input
              id="ai-model"
              type="text"
              className="settings-form__input"
              placeholder={activeProvider.defaultModel}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </div>

          <div className="settings-form__actions">
            <Button type="submit" variant="primary" id="ai-settings-save-btn">
              Save
            </Button>
            {saved && (
              <Button
                type="button"
                variant="ghost"
                leftIcon={<Trash2 size={14} />}
                onClick={handleClear}
                id="ai-settings-clear-btn"
              >
                Clear saved key
              </Button>
            )}
            {status === 'saved' && (
              <span className="settings-form__status settings-form__status--ok">
                <CheckCircle2 size={14} /> Saved to this browser
              </span>
            )}
            {status === 'cleared' && (
              <span className="settings-form__status">Cleared</span>
            )}
            {status === 'error' && (
              <span className="settings-form__status settings-form__status--error">
                Please paste a valid-looking API key first
              </span>
            )}
          </div>
        </form>
      </Card>

      <Card padding="default" className="settings-page__privacy">
        <ShieldCheck size={18} className="settings-page__privacy-icon" />
        <div>
          <strong>Your key never leaves your control.</strong> It is saved only in this
          browser’s local storage — WebGuard’s server never stores it. Each click of “Explain
          with AI” sends the key once, directly to the provider you chose, to generate that one
          answer; the AI only reads the findings a scan already produced and does not send any
          new request to the scanned site.
        </div>
      </Card>
    </div>
  )
}
