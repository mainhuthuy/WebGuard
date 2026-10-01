/* ============================================================
   Mock scan data — demo findings pool and result builder.
   Used by useScan while the backend API is not wired in (task 3.11).
   ============================================================ */

import type { ScanMode, ScanResult, ModuleName, Finding, Grade, Severity } from '../types'
import type { ModuleStep } from '../hooks/useScan'

/* ── Mock findings pool (for demo mode) ───────────────────── */

interface MockFinding {
  module: ModuleName
  severity: Severity
  title: string
  description: string
  remediation: string
  snippet?: string
  evidence?: string
}

const MOCK_FINDINGS_POOL: Record<ModuleName, MockFinding[]> = {
  headers: [
    {
      module: 'headers',
      severity: 'high',
      title: 'Missing Content-Security-Policy Header',
      description:
        'No Content-Security-Policy header was detected. This leaves the site vulnerable to Cross-Site Scripting (XSS) and data injection attacks.',
      remediation:
        "Add a Content-Security-Policy header to restrict resource loading. Start with a report-only policy and tighten it iteratively.",
      snippet:
        "Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
      evidence: 'Header not present in response',
    },
    {
      module: 'headers',
      severity: 'high',
      title: 'Missing Strict-Transport-Security (HSTS)',
      description:
        'The server does not enforce HTTPS via the Strict-Transport-Security header, allowing protocol downgrade attacks.',
      remediation:
        'Add the HSTS header with a minimum max-age of 31536000 (1 year) and include the includeSubDomains directive.',
      snippet: 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload',
      evidence: 'Header not present in response',
    },
    {
      module: 'headers',
      severity: 'medium',
      title: 'Missing X-Content-Type-Options Header',
      description:
        'Without X-Content-Type-Options: nosniff, browsers may MIME-sniff responses, potentially executing malicious content.',
      remediation: 'Set the X-Content-Type-Options header to "nosniff".',
      snippet: 'X-Content-Type-Options: nosniff',
      evidence: 'Header not present in response',
    },
    {
      module: 'headers',
      severity: 'medium',
      title: 'Missing Referrer-Policy Header',
      description:
        'No Referrer-Policy header was found. Full referrer URLs may be sent to third-party origins, leaking sensitive path information.',
      remediation: 'Set Referrer-Policy to "strict-origin-when-cross-origin" or "no-referrer".',
      snippet: 'Referrer-Policy: strict-origin-when-cross-origin',
      evidence: 'Header not present in response',
    },
  ],
  cookies: [
    {
      module: 'cookies',
      severity: 'high',
      title: 'Session Cookie Missing HttpOnly Flag',
      description:
        'The session cookie is accessible via JavaScript (document.cookie), making it vulnerable to XSS-based session hijacking.',
      remediation: 'Set the HttpOnly flag on all session and authentication cookies.',
      snippet: 'Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Lax',
      evidence: 'Set-Cookie: session_id=abc123; Path=/',
    },
    {
      module: 'cookies',
      severity: 'medium',
      title: 'Cookie Missing Secure Flag',
      description:
        'Cookies without the Secure flag can be sent over unencrypted HTTP connections, exposing them to interception.',
      remediation: 'Add the Secure flag to all cookies, especially session tokens.',
      snippet: 'Set-Cookie: token=xyz; Secure; HttpOnly; SameSite=Strict',
      evidence: 'Set-Cookie: token=xyz; Path=/',
    },
    {
      module: 'cookies',
      severity: 'low',
      title: 'Cookie Missing SameSite Attribute',
      description:
        'Cookies without SameSite may be sent in cross-origin requests, increasing CSRF risk.',
      remediation: 'Set SameSite=Lax or SameSite=Strict on all cookies.',
      snippet: 'Set-Cookie: pref=dark; SameSite=Lax; Secure',
      evidence: 'Set-Cookie: pref=dark; Path=/',
    },
  ],
  ssl_tls: [
    {
      module: 'ssl_tls',
      severity: 'critical',
      title: 'TLS 1.0 / 1.1 Still Supported',
      description:
        'The server accepts deprecated TLS 1.0/1.1 connections which have known vulnerabilities (POODLE, BEAST).',
      remediation:
        'Disable TLS 1.0 and 1.1 on the server. Only allow TLS 1.2 and TLS 1.3.',
      snippet: 'ssl_protocols TLSv1.2 TLSv1.3;  # Nginx example',
      evidence: 'TLSv1.0: enabled, TLSv1.1: enabled',
    },
    {
      module: 'ssl_tls',
      severity: 'medium',
      title: 'Certificate Expires Within 30 Days',
      description:
        'The SSL/TLS certificate will expire soon. Expired certificates cause browser warnings and loss of trust.',
      remediation:
        "Renew the certificate before expiration. Consider using automated renewal with Let's Encrypt / Certbot.",
      evidence: 'Expiry: 2026-10-20T00:00:00Z (24 days remaining)',
    },
  ],
  information: [
    {
      module: 'information',
      severity: 'medium',
      title: 'Server Version Disclosed',
      description:
        'The Server header reveals software and version information, helping attackers identify known vulnerabilities.',
      remediation:
        'Remove or obfuscate the Server header. In Nginx: server_tokens off;',
      snippet: 'server_tokens off;  # Nginx\nServerSignature Off  # Apache',
      evidence: 'Server: nginx/1.24.0',
    },
    {
      module: 'information',
      severity: 'high',
      title: 'Sensitive File Exposed: /.env',
      description:
        'The /.env file is publicly accessible and may contain API keys, database credentials, or other secrets.',
      remediation:
        'Block access to dotfiles in your web server configuration and remove .env from the web root.',
      snippet: 'location ~ /\\.(?!well-known) { deny all; }  # Nginx',
      evidence: 'HTTP 200 OK for GET /.env (487 bytes)',
    },
    {
      module: 'information',
      severity: 'info',
      title: 'robots.txt Exposes Internal Paths',
      description:
        'The robots.txt file lists paths that reveal application structure (e.g., /admin, /api/internal).',
      remediation:
        'Review robots.txt and remove references to sensitive paths. Use authentication instead of obscurity.',
      evidence: 'Disallow: /admin/\nDisallow: /api/internal/',
    },
  ],
  cors: [
    {
      module: 'cors',
      severity: 'critical',
      title: 'Wildcard Access-Control-Allow-Origin',
      description:
        'The server responds with Access-Control-Allow-Origin: *, allowing any website to read responses. Combined with credentials, this is a severe vulnerability.',
      remediation:
        'Replace the wildcard with an explicit allowlist of trusted origins.',
      snippet: "Access-Control-Allow-Origin: https://app.example.com",
      evidence: 'Access-Control-Allow-Origin: *',
    },
    {
      module: 'cors',
      severity: 'high',
      title: 'Origin Reflection Without Validation',
      description:
        'The server reflects the request Origin header verbatim in Access-Control-Allow-Origin without validating it against an allowlist.',
      remediation:
        'Validate the Origin header against a strict allowlist before reflecting it.',
      evidence:
        'Request Origin: https://evil.com → Response ACAO: https://evil.com',
    },
  ],
}

/** Pick N random findings from a module pool */
function pickFindings(mod: ModuleName, count: number): Finding[] {
  const pool = MOCK_FINDINGS_POOL[mod]
  const n = Math.min(count, pool.length)
  const shuffled = [...pool].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, n).map((f, i) => ({
    id: `${mod}-${i + 1}-${Date.now()}`,
    module: f.module,
    severity: f.severity,
    title: f.title,
    description: f.description,
    remediation: f.remediation,
    snippet: f.snippet,
    evidence: f.evidence,
  }))
}

/** Build a complete ScanResult from accumulated module steps */
export function buildMockScanResult(
  scanId: string,
  url: string,
  mode: ScanMode,
  moduleSteps: ModuleStep[],
  grade: Grade,
  score: number,
  startedAt: string,
): ScanResult {
  const findings: Finding[] = []
  for (const step of moduleSteps) {
    if (step.findingsCount > 0) {
      findings.push(...pickFindings(step.id, step.findingsCount))
    }
  }

  const summary = {
    critical: findings.filter((f) => f.severity === 'critical').length,
    high: findings.filter((f) => f.severity === 'high').length,
    medium: findings.filter((f) => f.severity === 'medium').length,
    low: findings.filter((f) => f.severity === 'low').length,
    info: findings.filter((f) => f.severity === 'info').length,
    total: findings.length,
  }

  const completedAt = new Date().toISOString()
  const durationMs = new Date(completedAt).getTime() - new Date(startedAt).getTime()

  return {
    scan_id: scanId,
    url,
    mode,
    status: 'completed',
    grade,
    score,
    findings,
    summary,
    started_at: startedAt,
    completed_at: completedAt,
    duration_ms: durationMs,
  }
}
