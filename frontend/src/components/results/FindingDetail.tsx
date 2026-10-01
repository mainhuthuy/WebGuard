import { useState, useCallback } from 'react'
import {
  ShieldCheck,
  FileCode2,
  Eye,
  Copy,
  Check,
  Info,
} from 'lucide-react'
import { Badge } from '../common'
import type { Finding, Severity } from '../../types'
import './FindingDetail.css'

/* ── Severity metadata ───────────────────────────────────── */

const SEVERITY_META: Record<Severity, { label: string; description: string }> = {
  critical: { label: 'Critical', description: 'Immediate exploitation risk — fix now' },
  high:     { label: 'High',     description: 'Serious vulnerability — fix in this sprint' },
  medium:   { label: 'Medium',   description: 'Moderate risk — plan a fix soon' },
  low:      { label: 'Low',      description: 'Minor issue — address when possible' },
  info:     { label: 'Info',     description: 'Informational observation — review only' },
}

/* ── Props ────────────────────────────────────────────────── */

interface FindingDetailProps {
  finding: Finding
}

/* ── Component ───────────────────────────────────────────── */

export default function FindingDetail({ finding }: FindingDetailProps) {
  const [copied, setCopied] = useState(false)
  const meta = SEVERITY_META[finding.severity]

  const handleCopy = useCallback(async () => {
    if (!finding.snippet) return
    try {
      await navigator.clipboard.writeText(finding.snippet)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for insecure contexts
      const textarea = document.createElement('textarea')
      textarea.value = finding.snippet
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [finding.snippet])

  return (
    <div className="finding-detail">
      {/* Severity colour strip */}
      <div
        className={`finding-detail__severity-strip finding-detail__severity-strip--${finding.severity}`}
      />

      {/* Header: badge + module */}
      <div className="finding-detail__header">
        <Badge variant={finding.severity} size="md" dot>
          {meta.label}
        </Badge>
        <span className="finding-detail__module-tag">{finding.module}</span>
        <span
          className="finding-detail__text"
          style={{ marginLeft: 'auto', fontSize: 'var(--text-xs)' }}
        >
          {meta.description}
        </span>
      </div>

      <hr className="finding-detail__divider" />

      {/* Description */}
      <div className="finding-detail__section">
        <div className="finding-detail__label">
          <Info className="finding-detail__label-icon" />
          Description
        </div>
        <div className="finding-detail__text">{finding.description}</div>
      </div>

      {/* Evidence */}
      {finding.evidence && (
        <div className="finding-detail__section">
          <div className="finding-detail__label">
            <Eye className="finding-detail__label-icon" />
            Evidence
          </div>
          <div className="finding-detail__evidence">{finding.evidence}</div>
        </div>
      )}

      <hr className="finding-detail__divider" />

      {/* Remediation */}
      <div className="finding-detail__section">
        <div className="finding-detail__label">
          <ShieldCheck className="finding-detail__label-icon" />
          Remediation
        </div>
        <div className="finding-detail__remediation">{finding.remediation}</div>
      </div>

      {/* Code snippet */}
      {finding.snippet && (
        <div className="finding-detail__section">
          <div className="finding-detail__label">
            <FileCode2 className="finding-detail__label-icon" />
            Recommended Fix
          </div>
          <div className="finding-detail__snippet-wrapper">
            <div className="finding-detail__snippet-bar">
              <span className="finding-detail__snippet-label">config / header</span>
              <button
                className={`finding-detail__copy-btn ${copied ? 'finding-detail__copy-btn--copied' : ''}`}
                onClick={handleCopy}
                title="Copy to clipboard"
              >
                {copied ? (
                  <>
                    <Check size={12} />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    Copy
                  </>
                )}
              </button>
            </div>
            <pre className="finding-detail__snippet-code">{finding.snippet}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
