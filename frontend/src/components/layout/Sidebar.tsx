import { useState } from 'react'
import {
  Shield,
  Search,
  History,
  FileText,
  Info,
  ChevronLeft,
  ChevronRight,
  Lock,
} from 'lucide-react'
import './Sidebar.css'

/** Single navigation item definition */
export interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  href: string
}

/** Navigation section with optional label */
export interface NavSection {
  label?: string
  items: NavItem[]
}

interface SidebarProps {
  /** Currently active route / page id */
  activeId?: string
  /** Called when user clicks a nav link */
  onNavigate?: (id: string, href: string) => void
  /** Controlled collapsed state (optional) */
  collapsed?: boolean
  /** Called when toggle button is clicked */
  onToggleCollapse?: () => void
}

/** Default navigation structure for WebGuard */
const defaultSections: NavSection[] = [
  {
    label: 'Scanner',
    items: [
      { id: 'scan', label: 'New Scan', icon: <Search size={20} />, href: '/' },
      { id: 'history', label: 'Scan History', icon: <History size={20} />, href: '/history' },
    ],
  },
  {
    label: 'Reports',
    items: [
      { id: 'reports', label: 'Export Reports', icon: <FileText size={20} />, href: '/reports' },
    ],
  },
  {
    label: 'Info',
    items: [
      { id: 'about', label: 'About & Disclaimer', icon: <Info size={20} />, href: '/about' },
    ],
  },
]

export default function Sidebar({
  activeId = 'scan',
  onNavigate,
  collapsed: controlledCollapsed,
  onToggleCollapse,
}: SidebarProps) {
  const [internalCollapsed, setInternalCollapsed] = useState(false)

  // Support both controlled and uncontrolled usage
  const isCollapsed = controlledCollapsed ?? internalCollapsed
  const handleToggle = onToggleCollapse ?? (() => setInternalCollapsed((c) => !c))

  const handleLinkClick = (item: NavItem, e: React.MouseEvent) => {
    e.preventDefault()
    onNavigate?.(item.id, item.href)
  }

  return (
    <>
      <aside
        className={`sidebar ${isCollapsed ? 'sidebar--collapsed' : ''}`}
        id="app-sidebar"
      >
        {/* Sidebar header */}
        <div className="sidebar__header">
          <a href="/" className="sidebar__brand">
            <Shield className="sidebar__logo-icon" />
            <span className="sidebar__logo-text">
              Web<span className="sidebar__logo-accent">Guard</span>
            </span>
          </a>
          <button
            className="sidebar__toggle"
            onClick={handleToggle}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Navigation links */}
        <nav className="sidebar__nav">
          {defaultSections.map((section, sIdx) => (
            <div key={sIdx}>
              {section.label && (
                <div className="sidebar__section-label">{section.label}</div>
              )}
              {section.items.map((item) => (
                <a
                  key={item.id}
                  href={item.href}
                  className={`sidebar__link ${
                    activeId === item.id ? 'sidebar__link--active' : ''
                  }`}
                  onClick={(e) => handleLinkClick(item, e)}
                  title={isCollapsed ? item.label : undefined}
                >
                  <span className="sidebar__link-icon">{item.icon}</span>
                  <span className="sidebar__link-text">{item.label}</span>
                </a>
              ))}
            </div>
          ))}
        </nav>

        {/* Sidebar footer */}
        <div className="sidebar__footer">
          <div className="sidebar__footer-content">
            <Lock className="sidebar__footer-icon" />
            <span className="sidebar__footer-text">Passive Audit Only</span>
          </div>
        </div>
      </aside>
    </>
  )
}
