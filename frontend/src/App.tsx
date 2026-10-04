import { lazy, Suspense, useState, useCallback } from 'react'
import { Header, Sidebar, Footer } from './components/layout'
import ScanPage from './pages/ScanPage'
import HistoryPage from './pages/HistoryPage'
import { Button } from './components/common'
import { ScanProgress } from './components/scanner'
import { useScan } from './hooks'
import { scanApi, mapScanDetail, toApiError } from './services'
import { buildMockResultFromHistory } from './utils/mockScan'
import { USE_MOCK } from './config'
import type { ScanHistoryItem, ScanMode, ScanResult } from './types'

// Results pulls in Recharts; About/Settings are rarely visited — keep all out of the main bundle
const ResultsPage = lazy(() => import('./pages/ResultsPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

/** App-level view state */
type AppView = 'scan' | 'progress' | 'results' | 'history' | 'reports' | 'about' | 'settings'

/** Where the currently displayed results came from (decides the back button) */
type ResultsSource = 'scan' | 'history'

function PageFallback() {
  return (
    <div className="page flex-center" style={{ minHeight: '40vh' }} role="status">
      <p className="text-secondary">Loading…</p>
    </div>
  )
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeNav, setActiveNav] = useState('scan')
  const [view, setView] = useState<AppView>('scan')

  // Scan lifecycle (state + SSE) lives in useScan
  const scan = useScan()
  const { startScan, cancelScan, reset: resetScan } = scan

  // A past scan opened from the history page
  const [historyResult, setHistoryResult] = useState<ScanResult | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [resultsSource, setResultsSource] = useState<ResultsSource>('scan')

  const handleNavigate = (id: string, _href: string) => {
    setActiveNav(id)
    if (id === 'scan') {
      // While a scan is running, "New Scan" returns to its live progress instead of resetting it
      setView(scan.scanning ? 'progress' : 'scan')
    } else {
      setHistoryError(null)
      setView(id as AppView)
    }
  }

  const handleStartScan = useCallback(
    (url: string, mode: ScanMode) => {
      startScan(url, mode)
      setResultsSource('scan')
      setView('progress')
      setActiveNav('scan')
    },
    [startScan],
  )

  const handleCancelScan = useCallback(() => {
    cancelScan()
    setView('scan')
  }, [cancelScan])

  const handleViewResults = useCallback(() => {
    setResultsSource('scan')
    setView('results')
    setActiveNav('scan')
  }, [])

  const handleNewScan = useCallback(() => {
    resetScan()
    setView('scan')
    setActiveNav('scan')
  }, [resetScan])

  const handleViewHistoryScan = useCallback(async (item: ScanHistoryItem) => {
    setHistoryError(null)
    try {
      const result = USE_MOCK
        ? buildMockResultFromHistory(item)
        : mapScanDetail(await scanApi.getScan(item.scan_id))
      setHistoryResult(result)
      setResultsSource('history')
      setView('results')
      setActiveNav('history')
    } catch (err) {
      setHistoryError(toApiError(err).message)
    }
  }, [])

  const handleBackFromResults = useCallback(() => {
    if (resultsSource === 'history') {
      setView('history')
      setActiveNav('history')
    } else {
      handleNewScan()
    }
  }, [resultsSource, handleNewScan])

  const shownResult = resultsSource === 'history' ? historyResult : scan.result

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
          {view === 'scan' && <ScanPage onStartScan={handleStartScan} scanning={scan.scanning} />}

          {/* Real-time progress */}
          {view === 'progress' && (
            <ScanProgress
              url={scan.scanUrl}
              progress={scan.progress}
              modules={scan.modules}
              logs={scan.logs}
              completed={scan.completed}
              errored={scan.errored}
              errorMessage={scan.errorMessage}
              onViewResults={handleViewResults}
              onCancel={handleCancelScan}
              onRetry={handleNewScan}
            />
          )}

          {/* Scan results */}
          {view === 'results' && shownResult && (
            <Suspense fallback={<PageFallback />}>
              <ResultsPage
                result={shownResult}
                onBack={handleBackFromResults}
                backLabel={resultsSource === 'history' ? 'Back to History' : 'New Scan'}
                onRescan={() => handleStartScan(shownResult.url, shownResult.mode)}
                onOpenAISettings={() => handleNavigate('settings', '/settings')}
              />
            </Suspense>
          )}

          {/* Scan history */}
          {view === 'history' && (
            <HistoryPage
              onNewScan={handleNewScan}
              onViewScan={handleViewHistoryScan}
              openError={historyError}
            />
          )}

          {view === 'reports' && (
            <div className="page flex-center" style={{ minHeight: '50vh', textAlign: 'center' }}>
              <div>
                <p
                  className="text-secondary"
                  style={{ fontSize: 'var(--text-lg)', marginBottom: 'var(--space-3)' }}
                >
                  📄 Export Reports
                </p>
                <p
                  className="text-secondary"
                  style={{ fontSize: 'var(--text-sm)', maxWidth: 400, margin: '0 auto var(--space-6)' }}
                >
                  Open a scan from the <strong>Scan History</strong> or finish a new scan, then use
                  the <strong>Export</strong> button on the Results page to download JSON or HTML.
                </p>
                <Button variant="primary" size="sm" onClick={handleNewScan}>
                  Start a Scan
                </Button>
              </div>
            </div>
          )}

          {view === 'about' && (
            <Suspense fallback={<PageFallback />}>
              <AboutPage onStartScan={() => handleNavigate('scan', '/')} />
            </Suspense>
          )}

          {view === 'settings' && (
            <Suspense fallback={<PageFallback />}>
              <SettingsPage />
            </Suspense>
          )}
        </main>

        <Footer hasSidebar sidebarCollapsed={sidebarCollapsed} />
      </div>
    </div>
  )
}
