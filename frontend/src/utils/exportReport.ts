/* ============================================================
   Export Report Utilities
   Client-side generation of JSON and HTML security reports.
   ============================================================ */

import type { ScanResult, Finding, Severity } from '../types'

/* ── Helpers ─────────────────────────────────────────────── */

/** Trigger file download from a Blob */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  setTimeout(() => {
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, 100)
}

/** Sanitise a URL into a safe filename segment */
function urlToFilename(url: string): string {
  try {
    const hostname = new URL(url).hostname
    return hostname.replace(/[^a-zA-Z0-9.-]/g, '_')
  } catch {
    return 'report'
  }
}

/** Format ISO date string for display */
function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return iso
  }
}

/** Format duration in ms */
function formatDuration(ms?: number): string {
  if (ms === undefined) return '—'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/* ── JSON Export ──────────────────────────────────────────── */

export function exportAsJson(result: ScanResult): void {
  const json = JSON.stringify(result, null, 2)
  const blob = new Blob([json], { type: 'application/json;charset=utf-8' })
  const filename = `webguard_${urlToFilename(result.url)}_${result.scan_id}.json`
  downloadBlob(blob, filename)
}

/* ── HTML Export ──────────────────────────────────────────── */

const SEVERITY_COLORS: Record<Severity, { accent: string; bg: string }> = {
  critical: { accent: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  high:     { accent: '#f97316', bg: 'rgba(249,115,22,0.15)' },
  medium:   { accent: '#eab308', bg: 'rgba(234,179,8,0.15)' },
  low:      { accent: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  info:     { accent: '#64748b', bg: 'rgba(100,116,139,0.15)' },
}

const GRADE_COLORS: Record<string, string> = {
  'A+': '#10b981',
  A: '#34d399',
  B: '#eab308',
  C: '#f97316',
  F: '#ef4444',
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function renderFinding(f: Finding): string {
  const sev = SEVERITY_COLORS[f.severity]
  return `
    <div class="finding-card" style="border-left-color:${sev.accent}">
      <div class="finding-header">
        <span class="finding-name">${escapeHtml(f.title)}</span>
        <span class="severity-badge" style="background:${sev.bg};color:${sev.accent}">
          ${f.severity.toUpperCase()}
        </span>
      </div>
      <div class="finding-module">Module: ${escapeHtml(f.module)}</div>
      <div class="finding-desc">${escapeHtml(f.description)}</div>
      ${f.evidence ? `
      <div class="finding-evidence">
        <strong>Evidence:</strong> ${escapeHtml(f.evidence)}
      </div>` : ''}
      <div class="finding-remediation">
        <strong>💡 Remediation:</strong> ${escapeHtml(f.remediation)}
      </div>
      ${f.snippet ? `
      <div class="finding-snippet">
        <div class="snippet-label">Recommended Fix</div>
        <pre>${escapeHtml(f.snippet)}</pre>
      </div>` : ''}
    </div>`
}

function buildHtmlReport(result: ScanResult): string {
  const gradeColor = GRADE_COLORS[result.grade] ?? '#6366f1'
  const generatedAt = formatDate(new Date().toISOString())

  const summaryItems = (['critical', 'high', 'medium', 'low', 'info'] as Severity[])
    .map((s) => {
      const sev = SEVERITY_COLORS[s]
      return `
      <div class="summary-item">
        <div class="count" style="color:${sev.accent}">${result.summary[s]}</div>
        <div class="label">${s.charAt(0).toUpperCase() + s.slice(1)}</div>
      </div>`
    })
    .join('')

  const findingsHtml =
    result.findings.length > 0
      ? result.findings.map((f) => renderFinding(f)).join('')
      : `<div class="no-findings">✅ No security issues detected. Excellent!</div>`

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WebGuard Report — ${escapeHtml(result.url)}</title>
  <style>
    :root {
      --bg-primary: #060912;
      --bg-card: #0d1220;
      --bg-header: #0d1220;
      --text-primary: #e2e8f0;
      --text-secondary: #94a3b8;
      --border: rgba(99,102,241,0.12);
      --accent: #6366f1;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.7;
      padding: 2rem;
    }
    .container { max-width: 900px; margin: 0 auto; }

    /* Header */
    .report-header {
      background: linear-gradient(135deg, #131a2e, #1a2340);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2.5rem;
      margin-bottom: 1.5rem;
      text-align: center;
    }
    .report-header h1 {
      font-size: 1.4rem;
      color: var(--accent);
      margin-bottom: 0.5rem;
      letter-spacing: -0.5px;
    }
    .report-header .target-url {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 1rem;
      color: var(--text-secondary);
      word-break: break-all;
    }
    .report-header .meta {
      margin-top: 1rem;
      font-size: 0.8rem;
      color: var(--text-secondary);
    }

    /* Score card */
    .score-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2rem;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: center;
      gap: 2rem;
    }
    .grade-circle {
      width: 100px; height: 100px;
      border-radius: 50%;
      display: flex;
      align-items: center; justify-content: center;
      font-size: 2.5rem; font-weight: 800;
      flex-shrink: 0;
      border: 4px solid ${gradeColor};
      color: ${gradeColor};
      box-shadow: 0 0 20px ${gradeColor}33;
    }
    .score-details h2 { font-size: 1.2rem; margin-bottom: 0.3rem; color: var(--text-secondary); }
    .score-details .score-value {
      font-size: 2rem; font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }
    .score-details .total-findings {
      color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.3rem;
    }

    /* Summary */
    .summary-bar {
      display: flex; gap: 0.75rem; margin-bottom: 1.5rem; flex-wrap: wrap;
    }
    .summary-item {
      background: var(--bg-card); border: 1px solid var(--border);
      border-radius: 12px; padding: 1rem 1.5rem;
      flex: 1; min-width: 100px; text-align: center;
    }
    .summary-item .count { font-size: 1.4rem; font-weight: 700; font-family: monospace; }
    .summary-item .label { font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

    /* Findings */
    .findings-section h2 {
      font-size: 1.1rem; color: var(--accent);
      margin-bottom: 1rem; padding-bottom: 0.5rem;
      border-bottom: 1px solid var(--border);
    }
    .finding-card {
      background: var(--bg-card); border: 1px solid var(--border);
      border-left: 4px solid var(--text-secondary);
      border-radius: 10px; padding: 1.2rem;
      margin-bottom: 0.75rem;
    }
    .finding-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .finding-name { font-weight: 600; font-size: 0.95rem; }
    .severity-badge {
      padding: 3px 12px; border-radius: 20px;
      font-size: 0.7rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.5px;
    }
    .finding-module { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.4rem; font-family: monospace; }
    .finding-desc { font-size: 0.85rem; margin-bottom: 0.5rem; color: var(--text-secondary); }
    .finding-evidence {
      font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;
      color: #f97316; background: rgba(249,115,22,0.06);
      border: 1px solid rgba(249,115,22,0.15); border-radius: 6px;
      padding: 0.5rem 0.8rem; margin-bottom: 0.5rem; word-break: break-all;
    }
    .finding-remediation {
      font-size: 0.85rem; color: #34d399;
      background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.12);
      padding: 0.5rem 0.8rem; border-radius: 6px; margin-bottom: 0.5rem;
    }
    .finding-snippet { margin-top: 0.5rem; }
    .snippet-label {
      font-family: monospace; font-size: 0.7rem;
      text-transform: uppercase; color: var(--text-secondary);
      letter-spacing: 0.5px; margin-bottom: 0.3rem;
    }
    .finding-snippet pre {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.8rem;
      color: #67e8f9; background: #060912; padding: 0.8rem 1rem;
      border-radius: 8px; border: 1px solid var(--border);
      overflow-x: auto; white-space: pre-wrap; line-height: 1.6;
    }
    .no-findings { text-align: center; padding: 3rem; color: #10b981; font-size: 1.1rem; }

    /* Footer */
    .report-footer {
      text-align: center; padding: 1.5rem;
      color: var(--text-secondary); font-size: 0.75rem;
      border-top: 1px solid var(--border); margin-top: 2rem;
    }

    @media print {
      body { background: #fff; color: #1a1a2e; padding: 1rem; }
      .report-header, .score-card, .summary-item, .finding-card { border-color: #ddd; background: #f9f9f9; }
      .finding-snippet pre { background: #f0f0f0; color: #333; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="report-header">
      <h1>🛡️ WebGuard — Security Assessment Report</h1>
      <div class="target-url">${escapeHtml(result.url)}</div>
      <div class="meta">
        Scan ID: <strong>${escapeHtml(result.scan_id)}</strong> ·
        Mode: <strong>${result.mode}</strong> ·
        Started: ${formatDate(result.started_at)}
        ${result.completed_at ? ` · Completed: ${formatDate(result.completed_at)}` : ''}
        ${result.duration_ms ? ` · Duration: ${formatDuration(result.duration_ms)}` : ''}
      </div>
    </div>

    <div class="score-card">
      <div class="grade-circle">${escapeHtml(result.grade)}</div>
      <div class="score-details">
        <h2>Overall Security Score</h2>
        <div class="score-value">${result.score} / 100</div>
        <div class="total-findings">${result.summary.total} issue${result.summary.total !== 1 ? 's' : ''} detected</div>
      </div>
    </div>

    <div class="summary-bar">${summaryItems}</div>

    <div class="findings-section">
      <h2>📋 Detailed Findings (${result.summary.total})</h2>
      ${findingsHtml}
    </div>

    <div class="report-footer">
      Report generated by <strong>WebGuard Security Scanner</strong> · ${generatedAt}
    </div>
  </div>
</body>
</html>`
}

export function exportAsHtml(result: ScanResult): void {
  const html = buildHtmlReport(result)
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const filename = `webguard_${urlToFilename(result.url)}_${result.scan_id}.html`
  downloadBlob(blob, filename)
}
