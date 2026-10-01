import { Github } from 'lucide-react'
import './Footer.css'

interface FooterProps {
  /** Whether sidebar is visible (offsets footer) */
  hasSidebar?: boolean
  /** Whether sidebar is collapsed */
  sidebarCollapsed?: boolean
}

export default function Footer({
  hasSidebar = true,
  sidebarCollapsed = false,
}: FooterProps) {
  const footerClass = [
    'footer',
    hasSidebar && !sidebarCollapsed && 'footer--with-sidebar',
    hasSidebar && sidebarCollapsed && 'footer--with-sidebar-collapsed',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <footer className={footerClass} id="app-footer">
      <div className="footer__left">
        <span>WebGuard</span>
        <span className="footer__separator">·</span>
        <span>Security Assessment Tool</span>
        <span className="footer__separator">·</span>
        <span>MIT License</span>
      </div>

      <div className="footer__right">
        <span>
          Made with <span className="footer__heart">♥</span> for learning
        </span>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="footer__link"
          title="View on GitHub"
        >
          <Github size={14} />
        </a>
      </div>
    </footer>
  )
}
