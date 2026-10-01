import { useState, useCallback } from 'react'
import { Header, Sidebar, Footer } from './components/layout'
import ScanPage from './pages/ScanPage'
import ResultsPage from './pages/ResultsPage'
import HistoryPage from './pages/HistoryPage'
import { Button } from './components/common'
import { ScanProgress } from './components/scanner'
import { useScan } from './hooks'
import type { ScanMode } from './types'

/** App-level view state */
type AppView = 'scan' | 'progress' | 'results' | 'history' | 'reports' | 'about'

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeNav, setActiveNav] = useState('scan')
  const [view, setView] = useState<AppView>('scan')

  // Scan lifecycle (state + SSE) lives in useScan
  const scan = useScan()

  const handleNavigate = (id: string, _href: string) => {
    setActiveNav(id)
    if (id === 'scan') {
      // Reset to scan form if not currently scanning
      if (!scan.scanning) {
        setView('scan')
      }
    } else {
      setView(id as AppView)
    }
  }

  const handleStartScan = useCallback(
    (url: string, mode: ScanMode) => {
      scan.startScan(url, mode)
      setView('progress')
      setActiveNav('scan')
    },
    [scan.startScan],
  )

  const handleCancelScan = useCallback(() => {
    scan.cancelScan()
    setView('scan')
  }, [scan.cancelScan])

  const handleViewResults = useCallback(() => {
    setView('results')
    setActiveNav('scan')
  }, [])

  const handleNewScan = useCallback(() => {
    scan.reset()
    setView('scan')
  }, [scan.reset])

  return (
    <div className="app-shell">
      {/* Sidebar navigation */}
      <Sidebar
        activeId={activeNav}
        onNavigate={handleNavigate}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
      />

      {/* Main content area */}
      <div className={`app-main ${sidebarCollapsed ? 'app-main--collapsed' : ''}`}>
        <Header hasSidebar sidebarCollapsed={sidebarCollapsed} engineOnline />

        <main className="app-content">
          {/* Scan input form */}
          {view === 'scan' && (
            <ScanPage onStartScan={handleStartScan} scanning={scan.scanning} />
          )}

          {/* Real-time progress */}
          {view === 'progress' && (
            <ScanProgress
              url={scan.scanUrl}
              progress={scan.progress}
              modules={scan.modules}
              logs={scan.logs}
              completed={scan.completed}
              errored={scan.errored}
              onViewResults={handleViewResults}
              onCancel={handleCancelScan}
            />
          )}

          {/* Scan results */}
          {view === 'results' && scan.result && (
            <ResultsPage
              result={scan.result}
              onBack={handleNewScan}
              onRescan={() => handleStartScan(scan.result!.url, scan.result!.mode)}
            />
          )}

          {/* Scan history */}
          {view === 'history' && (
            <HistoryPage
              onNewScan={handleNewScan}
              onViewScan={(scanId) => {
                // Future: load scan by ID and show ResultsPage
                console.log('[WebGuard] View scan:', scanId)
              }}
            />
          )}
          {view === 'reports' && (
            <div className="page flex-center" style={{ minHeight: '50vh', textAlign: 'center' }}>
              <div>
                <p className="text-secondary" style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-3)' }}>
                  📄 Export Reports
                </p>
                <p className="text-secondary" style={{ fontSize: 'var(--text-sm)', maxWidth: 400, margin: '0 auto var(--space-6)' }}>
                  Run a scan and click the <strong>Export</strong> button on the Results page to download reports in JSON or HTML format.
                </p>
                <Button variant="primary" size="sm" onClick={handleNewScan}>
                  Start a Scan
                </Button>
              </div>
            </div>
          )}
          {view === 'about' && (
            <div className="page flex-center" style={{ minHeight: '50vh' }}>
              <p className="text-secondary">About & Disclaimer — coming in task 3.12</p>
            </div>
          )}
        </main>

        <Footer hasSidebar sidebarCollapsed={sidebarCollapsed} />
      </div>
    </div>
  )
}
