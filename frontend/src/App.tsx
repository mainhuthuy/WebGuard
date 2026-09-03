import { Shield, Search, Terminal, AlertTriangle, CheckCircle2 } from 'lucide-react'

export default function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        borderBottom: '1px solid var(--border-color)',
        padding: '1rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(18, 24, 38, 0.5)',
        backdropFilter: 'blur(10px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Shield style={{ color: 'var(--primary)', width: '28px', height: '28px' }} />
          <span style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.025em' }}>
            Web<span style={{ color: 'var(--primary)' }}>Guard</span>
          </span>
          <span style={{
            fontSize: '0.75rem',
            padding: '0.15rem 0.5rem',
            borderRadius: '9999px',
            background: 'rgba(99, 102, 241, 0.15)',
            color: 'var(--primary)',
            fontWeight: 600,
          }}>
            v0.1.0-alpha
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          <span>Security Engine: <strong style={{ color: 'var(--accent-emerald)' }}>Ready</strong></span>
        </div>
      </header>

      {/* Hero Scanner Placeholder */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
        <div style={{
          maxWidth: '720px',
          width: '100%',
          textAlign: 'center',
        }}>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '1rem', letterSpacing: '-0.03em' }}>
            Automated Web <span style={{ color: 'var(--accent-cyan)' }}>Security Assessment</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: '2.5rem' }}>
            Audit security headers, SSL/TLS certificates, sensitive files disclosure, and misconfigurations.
          </p>

          {/* Search Box Mockup */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            padding: '0.5rem 0.75rem',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
          }}>
            <Search style={{ color: 'var(--text-muted)', width: '20px', height: '20px', marginLeft: '0.5rem' }} />
            <input
              type="text"
              placeholder="https://example.com"
              disabled
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                outline: 'none',
                padding: '0.5rem',
              }}
            />
            <button
              disabled
              style={{
                background: 'var(--primary)',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                padding: '0.65rem 1.25rem',
                fontWeight: 600,
                cursor: 'not-allowed',
                opacity: 0.8,
              }}
            >
              Scan Target
            </button>
          </div>

          {/* Badges preview */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginTop: '2rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <CheckCircle2 style={{ width: '16px', height: '16px', color: 'var(--accent-emerald)' }} /> Passive Auditing
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Terminal style={{ width: '16px', height: '16px', color: 'var(--accent-cyan)' }} /> Fast Async Engine
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <AlertTriangle style={{ width: '16px', height: '16px', color: 'var(--severity-medium)' }} /> Remediation Guides
            </span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-color)',
        padding: '1rem 2rem',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: '0.8rem',
      }}>
        WebGuard — Local Security Assessment Tool · MIT License
      </footer>
    </div>
  )
}
