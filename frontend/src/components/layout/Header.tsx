import { Shield } from 'lucide-react'
import './Header.css'

interface HeaderProps {
  /** Whether sidebar is visible (offsets header to the right) */
  hasSidebar?: boolean
  /** Whether sidebar is in collapsed state */
  sidebarCollapsed?: boolean
  /** Engine connection status */
  engineOnline?: boolean
}

export default function Header({
  hasSidebar = true,
  sidebarCollapsed = false,
  engineOnline = true,
}: HeaderProps) {
  const headerClass = [
    'header',
    hasSidebar && !sidebarCollapsed && 'header--with-sidebar',
    hasSidebar && sidebarCollapsed && 'header--with-sidebar-collapsed',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <header className={headerClass} id="app-header">
      {/* Brand / Logo */}
      <a href="/" className="header__brand">
        <Shield className="header__logo-icon" />
        <span className="header__logo-text">
          Web<span className="header__logo-accent">Guard</span>
        </span>
        <span className="header__version">v0.1.0</span>
      </a>

      {/* Right side */}
      <div className="header__actions">
        <div className="header__status">
          <div
            className={`header__status-dot ${
              !engineOnline ? 'header__status-dot--offline' : ''
            }`}
          />
          <span>Security Engine:</span>
          <span
            className={`header__status-label ${
              !engineOnline ? 'header__status-label--offline' : ''
            }`}
          >
            {engineOnline ? 'Online' : 'Offline'}
          </span>
        </div>
      </div>
    </header>
  )
}
