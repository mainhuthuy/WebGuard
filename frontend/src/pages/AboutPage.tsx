import {
  Info,
  ShieldCheck,
  FileLock2,
  Cookie,
  KeyRound,
  Globe2,
  Search,
  Activity,
  FileText,
  Scale,
  ShieldAlert,
  Ban,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Button, Card } from '../components/common'
import './AboutPage.css'

/* ── Content ─────────────────────────────────────────────── */

interface Feature {
  icon: ReactNode
  title: string
  description: string
}

const FEATURES: Feature[] = [
  {
    icon: <FileLock2 size={20} />,
    title: 'Security Headers',
    description:
      'Checks for CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy and cross-origin isolation headers.',
  },
  {
    icon: <Cookie size={20} />,
    title: 'Cookie Flags',
    description: 'Verifies that cookies set by the target use Secure, HttpOnly and SameSite.',
  },
  {
    icon: <KeyRound size={20} />,
    title: 'SSL / TLS',
    description:
      'Inspects the certificate expiry date and flags outdated protocol versions (SSLv3, TLS 1.0 and 1.1).',
  },
  {
    icon: <Search size={20} />,
    title: 'Information Disclosure',
    description:
      'Looks for exposed files such as /.env and /.git/HEAD, and for Server / X-Powered-By banners that leak technology details.',
  },
  {
    icon: <Globe2 size={20} />,
    title: 'CORS Configuration',
    description:
      'Detects wildcard origins, reflected origins and credentialed cross-origin access.',
  },
]

const STEPS: { title: string; description: string }[] = [
  {
    title: 'Enter a target',
    description: 'Paste the full URL (including http:// or https://) of a site you are allowed to test.',
  },
  {
    title: 'Watch the scan',
    description: 'Each module reports progress in real time as the audit runs.',
  },
  {
    title: 'Review the results',
    description:
      'See your grade, a severity breakdown, and per-finding remediation guidance.',
  },
  {
    title: 'Export the report',
    description: 'Download the full report as JSON or a self-contained HTML file.',
  },
]

const SCORING: { severity: string; penalty: number; color: string }[] = [
  { severity: 'Critical', penalty: 15, color: 'var(--severity-critical)' },
  { severity: 'High', penalty: 10, color: 'var(--severity-high)' },
  { severity: 'Medium', penalty: 5, color: 'var(--severity-medium)' },
  { severity: 'Low', penalty: 2, color: 'var(--severity-low)' },
]

const GRADES: { grade: string; range: string; color: string }[] = [
  { grade: 'A+', range: '95 – 100', color: 'var(--grade-a-plus)' },
  { grade: 'A', range: '85 – 94', color: 'var(--grade-a)' },
  { grade: 'B', range: '70 – 84', color: 'var(--grade-b)' },
  { grade: 'C', range: '50 – 69', color: 'var(--grade-c)' },
  { grade: 'F', range: '0 – 49', color: 'var(--grade-f)' },
]

const LIMITATIONS: string[] = [
  'WebGuard checks configuration only. It does not test for application-level vulnerabilities such as SQL injection or XSS.',
  'A high grade does not mean a site is secure, and a low grade does not mean it has been compromised.',
  'Results reflect a single point in time and may include false positives or miss issues.',
  'Targets on private networks and localhost are blocked by design.',
]

/* ── Props ───────────────────────────────────────────────── */

interface AboutPageProps {
  /** Navigate to the scan form */
  onStartScan?: () => void
}

/* ── Page ────────────────────────────────────────────────── */

export default function AboutPage({ onStartScan }: AboutPageProps) {
  return (
    <div className="about-page">
      {/* Header */}
      <div className="about-page__header">
        <h1 className="about-page__title">
          <Info className="about-page__title-icon" />
          About &amp; Disclaimer
        </h1>
        <p className="about-page__lead">
          WebGuard is a web security assessment tool that audits a site's configuration for common
          misconfigurations and explains how to fix them.
        </p>
      </div>

      {/* Features */}
      <section className="about-section" aria-labelledby="about-features">
        <h2 className="about-section__title" id="about-features">
          <ShieldCheck size={18} /> What it checks
        </h2>
        <div className="about-grid">
          {FEATURES.map((f) => (
            <Card key={f.title} variant="flat" className="about-feature">
              <span className="about-feature__icon">{f.icon}</span>
              <h3 className="about-feature__title">{f.title}</h3>
              <p className="about-feature__desc">{f.description}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* How to use */}
      <section className="about-section" aria-labelledby="about-howto">
        <h2 className="about-section__title" id="about-howto">
          <Activity size={18} /> How to use
        </h2>
        <ol className="about-steps">
          {STEPS.map((s, i) => (
            <li key={s.title} className="about-steps__item">
              <span className="about-steps__num">{i + 1}</span>
              <div>
                <h3 className="about-steps__title">{s.title}</h3>
                <p className="about-steps__desc">{s.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Scoring */}
      <section className="about-section" aria-labelledby="about-scoring">
        <h2 className="about-section__title" id="about-scoring">
          <FileText size={18} /> How scoring works
        </h2>
        <p className="about-section__text">
          Every scan starts at 100 points. Each finding subtracts points based on its severity, and
          the final score maps to a letter grade.
        </p>
        <div className="about-scoring">
          <Card variant="flat" className="about-table-card">
            <h3 className="about-table__heading">Penalty per finding</h3>
            <ul className="about-table">
              {SCORING.map((s) => (
                <li key={s.severity} className="about-table__row">
                  <span className="about-table__label" style={{ color: s.color }}>
                    {s.severity}
                  </span>
                  <span className="about-table__value">−{s.penalty}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card variant="flat" className="about-table-card">
            <h3 className="about-table__heading">Grade scale</h3>
            <ul className="about-table">
              {GRADES.map((g) => (
                <li key={g.grade} className="about-table__row">
                  <span className="about-table__label" style={{ color: g.color }}>
                    {g.grade}
                  </span>
                  <span className="about-table__value">{g.range}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="about-section" aria-labelledby="about-disclaimer">
        <h2 className="about-section__title" id="about-disclaimer">
          <Scale size={18} /> Disclaimer
        </h2>
        <Card variant="flat" accent="primary" className="about-disclaimer">
          <div className="about-disclaimer__block about-disclaimer__block--warn">
            <ShieldAlert className="about-disclaimer__icon" />
            <div>
              <h3 className="about-disclaimer__heading">Authorized use only</h3>
              <p>
                Only scan websites that you own or that you have explicit written permission to
                test. Scanning systems without authorization may be illegal in your jurisdiction.
                You are solely responsible for how you use this tool.
              </p>
            </div>
          </div>

          <div className="about-disclaimer__block">
            <Ban className="about-disclaimer__icon" />
            <div>
              <h3 className="about-disclaimer__heading">Non-intrusive, but not invisible</h3>
              <p>
                WebGuard sends a small number of ordinary read-only HTTP requests and one TLS
                handshake, and does not attempt exploitation. These requests will still appear in
                the target's server logs.
              </p>
            </div>
          </div>

          <div className="about-disclaimer__block">
            <Scale className="about-disclaimer__icon" />
            <div>
              <h3 className="about-disclaimer__heading">No warranty</h3>
              <p>
                The software and its reports are provided &ldquo;as is&rdquo; without warranty of
                any kind. The authors are not liable for any damage or loss arising from the use of
                this tool or from decisions made based on its results.
              </p>
            </div>
          </div>

          <h3 className="about-disclaimer__heading about-disclaimer__heading--list">
            Limitations
          </h3>
          <ul className="about-disclaimer__list">
            {LIMITATIONS.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </Card>
      </section>

      {onStartScan && (
        <div className="about-page__cta">
          <Button variant="primary" size="md" onClick={onStartScan} id="about-start-scan-btn">
            Start a scan
          </Button>
        </div>
      )}
    </div>
  )
}
