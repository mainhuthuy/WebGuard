import { useState, useRef, useEffect, useCallback } from 'react'
import {
  ArrowLeft,
  Download,
  RefreshCw,
  ChevronRight,
  ShieldCheck,
  FileJson,
  FileText,
} from 'lucide-react'
import { ScoreCard, SeverityChart, FindingDetail } from '../components/results'
import { Card, Badge, Button, Modal } from '../components/common'
import { useReport } from '../hooks/useReport'
import type { ScanResult, Severity, Finding } from '../types'
import './ResultsPage.css'

const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

interface ResultsPageProps {
  result: ScanResult
  onBack?: () => void
  onRescan?: () => void
  /** Label of the back button. @default 'New Scan' */
  backLabel?: string
}

export default function ResultsPage({
  result,
  onBack,
  onRescan,
  backLabel = 'New Scan',
}: ResultsPageProps) {
  const [activeFilter, setActiveFilter] = useState<Severity | 'all'>('all')
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const exportRef = useRef<HTMLDivElement>(null)

  // Close export dropdown on outside click
  useEffect(() => {
    if (!exportOpen) return
    const handler = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [exportOpen])

  const { exportReport } = useReport()

  const handleExportJson = useCallback(() => {
    exportReport(result, 'json')
    setExportOpen(false)
  }, [result, exportReport])

  const handleExportHtml = useCallback(() => {
    exportReport(result, 'html')
    setExportOpen(false)
  }, [result, exportReport])

  const filteredFindings =
    activeFilter === 'all'
      ? result.findings
      : result.findings.filter((f) => f.severity === activeFilter)

  return (
    <div className="results-page">
      {/* Top bar */}
      <div className="results-page__topbar">
        <button className="results-page__back" onClick={onBack}>
          <ArrowLeft size={16} />
          {backLabel}
        </button>
        <div className="results-page__actions">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<RefreshCw size={14} />}
            onClick={onRescan}
          >
            Rescan
          </Button>
          <div className="export-dropdown" ref={exportRef}>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Download size={14} />}
              onClick={() => setExportOpen((o) => !o)}
              id="export-btn"
            >
              Export
            </Button>
            {exportOpen && (
              <div className="export-dropdown__menu">
                <button
                  className="export-dropdown__item"
                  onClick={handleExportJson}
                  id="export-json-btn"
                >
                  <FileJson size={16} />
                  <div>
                    <div className="export-dropdown__item-title">JSON Report</div>
                    <div className="export-dropdown__item-desc">Raw data, machine-readable</div>
                  </div>
                </button>
                <button
                  className="export-dropdown__item"
                  onClick={handleExportHtml}
                  id="export-html-btn"
                >
                  <FileText size={16} />
                  <div>
                    <div className="export-dropdown__item-title">HTML Report</div>
                    <div className="export-dropdown__item-desc">Styled report, shareable</div>
                  </div>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Overview: Score + Chart */}
      <div className="results-page__overview">
        <Card variant="glow" accent="primary">
          <ScoreCard
            grade={result.grade}
            score={result.score}
            url={result.url}
            duration={result.duration_ms}
          />
        </Card>
        <Card>
          <SeverityChart summary={result.summary} />
        </Card>
      </div>

      {/* Findings section */}
      <div>
        <div className="results-page__findings-header">
          <h3 className="results-page__findings-title">Findings</h3>
          <span className="results-page__findings-count">
            {result.summary.total} total
          </span>
        </div>

        {/* Severity filter chips */}
        <div className="results-filters">
          <button
            className={`results-filter ${activeFilter === 'all' ? 'results-filter--active' : ''}`}
            onClick={() => setActiveFilter('all')}
          >
            All ({result.summary.total})
          </button>
          {SEVERITY_ORDER.map((s) => {
            const count = result.summary[s]
            if (count === 0) return null
            return (
              <button
                key={s}
                className={`results-filter ${activeFilter === s ? 'results-filter--active' : ''}`}
                onClick={() => setActiveFilter(s)}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)} ({count})
              </button>
            )
          })}
        </div>

        {/* Findings list */}
        {filteredFindings.length > 0 ? (
          <div className="findings-list">
            {filteredFindings.map((finding) => (
              <div
                key={finding.id}
                className="finding-row"
                onClick={() => setSelectedFinding(finding)}
                id={`finding-${finding.id}`}
              >
                <div className={`finding-row__severity finding-row__severity--${finding.severity}`} />
                <div className="finding-row__content">
                  <div className="finding-row__title">{finding.title}</div>
                  <div className="finding-row__description">{finding.description}</div>
                </div>
                <div className="finding-row__meta">
                  <Badge variant={finding.severity} size="sm">{finding.severity}</Badge>
                  <span className="finding-row__module">{finding.module}</span>
                  <ChevronRight className="finding-row__chevron" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="findings-empty">
            <ShieldCheck className="findings-empty__icon" />
            <div className="findings-empty__text">All checks passed — no issues found!</div>
          </div>
        )}
      </div>

      {/* Finding detail modal */}
      <Modal
        open={selectedFinding !== null}
        onClose={() => setSelectedFinding(null)}
        title={selectedFinding?.title}
        size="lg"
      >
        {selectedFinding && <FindingDetail finding={selectedFinding} />}
      </Modal>
    </div>
  )
}
