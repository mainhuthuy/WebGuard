import { useState, type FormEvent } from 'react'
import {
  Search,
  Zap,
  ShieldCheck,
  Terminal,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react'
import { Button } from '../components/common'
import type { ScanMode, ModuleName } from '../types'
import './ScanPage.css'

/** Module definitions with metadata */
const ALL_MODULES: { id: ModuleName; label: string }[] = [
  { id: 'headers', label: 'Security Headers' },
  { id: 'cookies', label: 'Cookie Flags' },
  { id: 'ssl_tls', label: 'SSL/TLS' },
  { id: 'information', label: 'Info Disclosure' },
  { id: 'cors', label: 'CORS Config' },
]

/** Which modules each mode runs */
const MODE_MODULES: Record<ScanMode, ModuleName[]> = {
  quick: ['headers', 'ssl_tls'],
  full: ['headers', 'cookies', 'ssl_tls', 'information', 'cors'],
}

/** Basic URL validation */
function isValidUrl(value: string): boolean {
  try {
    const url = new URL(value)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}

interface ScanPageProps {
  /** Called when scan is submitted */
  onStartScan?: (url: string, mode: ScanMode) => void
  /** Whether a scan is currently running */
  scanning?: boolean
}

export default function ScanPage({ onStartScan, scanning = false }: ScanPageProps) {
  const [url, setUrl] = useState('')
  const [mode, setMode] = useState<ScanMode>('full')
  const [error, setError] = useState<string | null>(null)

  const activeModules = MODE_MODULES[mode]

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    const trimmed = url.trim()

    if (!trimmed) {
      setError('Please enter a target URL.')
      return
    }

    // Auto-prepend https:// if no protocol
    const finalUrl = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`

    if (!isValidUrl(finalUrl)) {
      setError('Please enter a valid URL (e.g., https://example.com).')
      return
    }

    setUrl(finalUrl)
    onStartScan?.(finalUrl, mode)
  }

  return (
    <div className="scan-page">
      <div className="scan-page__content anim-fade-in-up">
        {/* Hero text */}
        <h1 className="scan-page__title">
          Automated Web{' '}
          <span className="text-gradient-cyan">Security Assessment</span>
        </h1>
        <p className="scan-page__subtitle">
          Audit security headers, SSL/TLS certificates, sensitive file disclosure,
          and misconfigurations — in seconds.
        </p>

        {/* Scan form */}
        <form className="scan-form" onSubmit={handleSubmit}>
          {/* URL input */}
          <div className="scan-form__input-row">
            <Search className="scan-form__icon" />
            <input
              id="scan-url-input"
              type="text"
              className="scan-form__input"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                if (error) setError(null)
              }}
              autoComplete="url"
              spellCheck={false}
              disabled={scanning}
            />
            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={scanning}
              className="scan-form__submit"
              leftIcon={<Zap size={16} />}
              id="scan-submit-btn"
            >
              {scanning ? 'Scanning...' : 'Scan Target'}
            </Button>
          </div>

          {/* Validation error */}
          {error && (
            <div className="scan-form__error">
              <AlertCircle className="scan-form__error-icon" />
              {error}
            </div>
          )}

          {/* Scan mode selector */}
          <div className="scan-mode">
            <button
              type="button"
              className={`scan-mode__option ${mode === 'quick' ? 'scan-mode__option--active' : ''}`}
              onClick={() => setMode('quick')}
              id="scan-mode-quick"
            >
              <Zap className="scan-mode__icon" />
              <div className="scan-mode__label">
                <span className="scan-mode__name">Quick Scan</span>
                <span className="scan-mode__desc">Headers + SSL only</span>
              </div>
            </button>

            <button
              type="button"
              className={`scan-mode__option ${mode === 'full' ? 'scan-mode__option--active' : ''}`}
              onClick={() => setMode('full')}
              id="scan-mode-full"
            >
              <ShieldCheck className="scan-mode__icon" />
              <div className="scan-mode__label">
                <span className="scan-mode__name">Full Audit</span>
                <span className="scan-mode__desc">All 5 modules</span>
              </div>
            </button>
          </div>

          {/* Active modules chips */}
          <div className="scan-modules">
            {ALL_MODULES.map((mod) => {
              const isActive = activeModules.includes(mod.id)
              return (
                <div
                  key={mod.id}
                  className={`scan-modules__chip ${isActive ? 'scan-modules__chip--active' : ''}`}
                >
                  <span className="scan-modules__chip-dot" />
                  {mod.label}
                </div>
              )
            })}
          </div>
        </form>

        {/* Feature badges */}
        <div className="scan-features">
          <span className="scan-features__item">
            <CheckCircle2 className="scan-features__icon" style={{ color: 'var(--emerald)' }} />
            Non-intrusive Auditing
          </span>
          <span className="scan-features__item">
            <Terminal className="scan-features__icon" style={{ color: 'var(--cyan)' }} />
            Fast Async Engine
          </span>
          <span className="scan-features__item">
            <AlertTriangle className="scan-features__icon" style={{ color: 'var(--severity-medium)' }} />
            Remediation Guides
          </span>
        </div>
      </div>
    </div>
  )
}
