/* ============================================================
   Catalogue of everything WebGuard checks, shown on the About page.
   Keep in sync with backend/app/modules/* (names and severities).
   ============================================================ */

import type { ModuleName, ScanMode } from '../types'

export type CheckSeverity = 'critical' | 'high' | 'medium' | 'low'

export interface CheckInfo {
  /** Name as it appears in scan results */
  name: string
  severity: CheckSeverity
  /** What the scanner looks for */
  what: string
  /** Why it matters when the check fails */
  risk: string
}

export interface CheckModule {
  id: ModuleName
  title: string
  summary: string
  /** Scan modes that include this module */
  modes: ScanMode[]
  checks: CheckInfo[]
}

export const SEVERITY_GUIDE: { severity: CheckSeverity; label: string; meaning: string; penalty: number }[] = [
  {
    severity: 'critical',
    label: 'Critical',
    meaning: 'Immediate danger: secrets are exposed, or traffic and accounts can be taken over. Fix these first.',
    penalty: 15,
  },
  {
    severity: 'high',
    label: 'High',
    meaning: 'A serious weakness that makes real attacks easy (script injection, interception). Fix soon.',
    penalty: 10,
  },
  {
    severity: 'medium',
    label: 'Medium',
    meaning: 'A missing layer of defence, or information that helps an attacker. Plan a fix.',
    penalty: 5,
  },
  {
    severity: 'low',
    label: 'Low',
    meaning: 'Minor hardening or informational. Fix when convenient.',
    penalty: 2,
  },
]

export const CHECK_MODULES: CheckModule[] = [
  {
    id: 'headers',
    title: 'Security Headers',
    summary:
      'HTTP response headers that tell the browser how to protect visitors. A finding is reported for every header that is missing.',
    modes: ['quick', 'full'],
    checks: [
      {
        name: 'Content-Security-Policy',
        severity: 'high',
        what: 'Restricts where scripts, styles and images may be loaded from.',
        risk: 'Without it, an injected script (XSS) runs freely and can steal sessions or rewrite the page.',
      },
      {
        name: 'Strict-Transport-Security (HSTS)',
        severity: 'high',
        what: 'Tells browsers to always use HTTPS for this site.',
        risk: 'Visitors on hostile networks can be downgraded to plain HTTP, exposing logins and cookies.',
      },
      {
        name: 'X-Frame-Options',
        severity: 'medium',
        what: 'Controls whether other sites may embed the page in a frame.',
        risk: 'Clickjacking: a malicious page overlays an invisible frame to trick users into clicking.',
      },
      {
        name: 'X-Content-Type-Options',
        severity: 'medium',
        what: 'Stops the browser from guessing a file’s type (MIME sniffing).',
        risk: 'An uploaded text or image file could be treated as a script and executed.',
      },
      {
        name: 'Permissions-Policy',
        severity: 'medium',
        what: 'Restricts browser features such as camera, microphone and location.',
        risk: 'Injected or third-party scripts may request sensitive device features.',
      },
      {
        name: 'Cross-Origin-Opener-Policy',
        severity: 'medium',
        what: 'Isolates the page from windows opened by other origins.',
        risk: 'Weakens protection against cross-window and side-channel attacks such as Spectre.',
      },
      {
        name: 'Cross-Origin-Embedder-Policy',
        severity: 'medium',
        what: 'Requires cross-origin resources to opt in before they can be loaded.',
        risk: 'Cross-origin content loads without consent, which blocks strong browser isolation.',
      },
      {
        name: 'X-XSS-Protection',
        severity: 'low',
        what: 'Legacy switch for the old built-in browser XSS filter.',
        risk: 'Obsolete in modern browsers (CSP replaces it); only matters for very old ones.',
      },
      {
        name: 'Referrer-Policy',
        severity: 'low',
        what: 'Limits how much of the page URL is sent to other sites when a link is followed.',
        risk: 'URLs that contain tokens or IDs can leak to third parties.',
      },
    ],
  },
  {
    id: 'cookies',
    title: 'Cookie Flags',
    summary:
      'Security flags on the cookies the server sets when the page is requested. Each missing flag is reported per cookie.',
    modes: ['full'],
    checks: [
      {
        name: 'Secure',
        severity: 'high',
        what: 'The cookie is only sent over encrypted HTTPS connections.',
        risk: 'The cookie can travel in plain text on an insecure network, where anyone can read it and hijack the session.',
      },
      {
        name: 'HttpOnly',
        severity: 'high',
        what: 'JavaScript on the page cannot read the cookie.',
        risk: 'A single XSS bug lets an attacker steal the session cookie and log in as the victim.',
      },
      {
        name: 'SameSite',
        severity: 'medium',
        what: 'The browser does not attach the cookie to requests started by other sites.',
        risk: 'Cross-site request forgery (CSRF): another site can trigger actions using the visitor’s logged-in session.',
      },
    ],
  },
  {
    id: 'ssl_tls',
    title: 'SSL / TLS',
    summary:
      'The encrypted connection and its certificate. The scanner also tries TLS 1.0 and 1.1 separately to see whether the server still accepts them.',
    modes: ['quick', 'full'],
    checks: [
      {
        name: 'ssl_connection_failed',
        severity: 'critical',
        what: 'A secure connection could not be established (no HTTPS, invalid or self-signed certificate, wrong hostname).',
        risk: 'Traffic cannot be trusted or is unencrypted; browsers warn users and attackers can intercept it.',
      },
      {
        name: 'cert_expired',
        severity: 'critical',
        what: 'The certificate is past its expiry date.',
        risk: 'Browsers block or warn; users learn to click through warnings, which attackers exploit.',
      },
      {
        name: 'outdated_tls_version',
        severity: 'high',
        what: 'The server still accepts TLS 1.0 or TLS 1.1 (checked by trying each version).',
        risk: 'These old protocols have known weaknesses that allow traffic to be downgraded or decrypted.',
      },
      {
        name: 'cert_expiring_soon',
        severity: 'medium',
        what: 'The certificate expires in less than 30 days.',
        risk: 'An unnoticed expiry causes an outage and browser warnings.',
      },
    ],
  },
  {
    id: 'information',
    title: 'Information Disclosure',
    summary:
      'Files and response headers that reveal secrets or details about the technology behind the site.',
    modes: ['full'],
    checks: [
      {
        name: '/.env',
        severity: 'critical',
        what: 'A publicly readable environment file.',
        risk: 'It often holds database passwords and API keys, which can lead to a full compromise.',
      },
      {
        name: '/.git/HEAD',
        severity: 'critical',
        what: 'Exposed git repository metadata.',
        risk: 'Attackers can download the whole source code and history, including old secrets.',
      },
      {
        name: '/wp-admin',
        severity: 'medium',
        what: 'A WordPress admin entry point is reachable (directly or via a redirect to the login page).',
        risk: 'Reveals the CMS and invites password-guessing and plugin-exploit attempts.',
      },
      {
        name: 'Server header',
        severity: 'medium',
        what: 'The response names the web server software and version.',
        risk: 'Attackers can look up known vulnerabilities for that exact version.',
      },
      {
        name: 'X-Powered-By header',
        severity: 'medium',
        what: 'The response names the framework or language in use.',
        risk: 'Same as above: it narrows down which known exploits to try.',
      },
      {
        name: '/robots.txt',
        severity: 'low',
        what: 'A robots.txt file exists.',
        risk: 'Informational: it can reveal hidden paths (such as /admin) that crawlers are told to skip.',
      },
    ],
  },
  {
    id: 'cors',
    title: 'CORS Configuration',
    summary:
      'Which other websites may read responses from this site. The scanner sends a request with a fake origin to see how the server reacts.',
    modes: ['full'],
    checks: [
      {
        name: 'cors_origin_reflection',
        severity: 'critical',
        what: 'The server echoes back whatever origin it receives (tested with a fake origin).',
        risk: 'Every website is effectively trusted, so any site can read this site’s responses.',
      },
      {
        name: 'cors_credentials_exposed',
        severity: 'critical',
        what: 'A reflected origin combined with Access-Control-Allow-Credentials: true.',
        risk: 'A malicious site can make requests as the logged-in visitor and read private data (account takeover).',
      },
      {
        name: 'cors_wildcard',
        severity: 'high',
        what: 'Access-Control-Allow-Origin is “*”, so any website may read responses.',
        risk: 'Unsafe if the responses are not meant to be public; harmless for genuinely public data.',
      },
    ],
  },
]

/** Total number of distinct checks across all modules */
export const TOTAL_CHECKS = CHECK_MODULES.reduce((sum, m) => sum + m.checks.length, 0)
