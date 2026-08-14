import React, { useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import {
  ChevronLeft, ChevronRight, Upload,
  GraduationCap, Scan, AlertTriangle, CheckCircle,
  RefreshCw, ChevronDown, BookOpen, Minus, Plus
} from 'lucide-react';


pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

// ── Mock AI analysis data ─────────────────────────────────────────────────────
interface Finding {
  id: string;
  type: 'critical' | 'outdated' | 'aligned';
  title: string;
  original: string;
  updated: string;
}

const MOCK_FINDINGS: Finding[] = [
  {
    id: '1',
    type: 'critical',
    title: 'Financial Evaluation',
    original: 'Financial Evaluation',
    updated: 'Make sure to consider modern compliance standards when evaluating financials.',
  },
  {
    id: '2',
    type: 'outdated',
    title: 'Time Schedule',
    original: 'Time Schedule',
    updated: 'The time schedule should account for agile development phases, not just fixed weeks.',
  },
  {
    id: '3',
    type: 'aligned',
    title: 'Recurrent Costs',
    original: 'Recurrent Costs',
    updated: 'This correctly identifies post-warranty service period costs.',
  },
];

const typeConfig = {
  critical: { color: '#dc2626', bg: '#fee2e2', border: '#fca5a5', label: 'Critical Update', icon: AlertTriangle },
  outdated: { color: '#d97706', bg: '#fef9c3', border: '#fcd34d', label: 'Outdated Content', icon: AlertTriangle },
  aligned: { color: '#059669', bg: '#dcfce7', border: '#6ee7b7', label: 'Up to Date', icon: CheckCircle },
};

// ── Reader View ───────────────────────────────────────────────────────────────
interface ReaderViewProps {
  file: File;
  url: string;
  onReset: () => void;
}

export const ReaderView: React.FC<ReaderViewProps> = ({ file, url, onReset }) => {
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.1);
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [activeFinding, setActiveFinding] = useState<Finding | null>(null);
  const [selectedPages, setSelectedPages] = useState<string>('');
  const [scanMode, setScanMode] = useState<'current' | 'range' | 'all'>('current');

  // Grammarly-style highlight renderer
  const textRenderer = useCallback((textItem: any) => {
    const { str } = textItem;
    if (!str || str.trim().length < 4) return str;

    const matchedFinding = findings.find(f => 
      f.original.includes(str.trim()) || str.trim().includes(f.original)
    );

    if (matchedFinding) {
      return `<mark class="grammar-${matchedFinding.type}">${str}</mark>`;
    }
    return str;
  }, [findings]);

  const goTo = (p: number) => setCurrentPage(Math.max(1, Math.min(p, numPages)));

  const startScan = useCallback(async () => {
    setScanning(true);
    setScanProgress(0);
    setFindings([]);
    setActiveFinding(null);

    try {
      let pagesToScan: number[] = [];
      if (scanMode === 'current') {
        pagesToScan = [currentPage];
      } else if (scanMode === 'all') {
        pagesToScan = Array.from({ length: numPages }, (_, i) => i + 1);
      } else {
        const parts = selectedPages.split(',');
        for (const part of parts) {
          const p = part.trim();
          if (p.includes('-')) {
            const [start, end] = p.split('-').map(Number);
            if (!isNaN(start) && !isNaN(end)) {
              for (let i = start; i <= end; i++) pagesToScan.push(i);
            }
          } else {
            const n = Number(p);
            if (!isNaN(n)) pagesToScan.push(n);
          }
        }
      }

      if (pagesToScan.length === 0) {
        alert("No valid pages selected to scan.");
        setScanning(false);
        return;
      }

      setScanProgress(10);
      const doc = await pdfjs.getDocument(url).promise;
      let extractedText = "";
      for (let i = 0; i < pagesToScan.length; i++) {
        const pageNum = pagesToScan[i];
        if (pageNum < 1 || pageNum > numPages) continue;
        const page = await doc.getPage(pageNum);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map((item: any) => item.str).join(" ");
        extractedText += `--- Page ${pageNum} ---\n${pageText}\n\n`;
        setScanProgress(10 + Math.round(((i + 1) / pagesToScan.length) * 30));
      }

      if (!extractedText.trim()) {
        alert("No text could be extracted from these pages.");
        setScanning(false);
        return;
      }

      setScanProgress(50);

      // Simulate backend processing delay
      await new Promise(resolve => setTimeout(resolve, 800));
      setScanProgress(90);

      await new Promise(resolve => setTimeout(resolve, 400));
      
      // Return mock findings
      setFindings(MOCK_FINDINGS);
      setScanProgress(100);

    } catch (err) {
      console.error(err);
      alert("An error occurred during scanning. See console.");
    } finally {
      setTimeout(() => setScanning(false), 400);
    }
  }, [scanMode, currentPage, numPages, selectedPages, url]);

  // Parse page count label
  const scanLabel = () => {
    if (scanMode === 'current') return `Scan Page ${currentPage}`;
    if (scanMode === 'all') return `Scan All ${numPages} Pages`;
    return `Scan Selected Pages`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f5f6f8', overflow: 'hidden' }}>

      {/* ── Top Bar ── */}
      <header style={{
        height: 56, background: '#fff', borderBottom: '1px solid #e5e7eb',
        display: 'flex', alignItems: 'center', padding: '0 20px', gap: 16,
        flexShrink: 0, boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8 }}>
          <div style={{ width: 32, height: 32, background: '#0d3d2e', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <GraduationCap size={17} color="#fff" />
          </div>
          <span style={{ fontWeight: 800, fontSize: 15, color: '#0d3d2e' }}>Lumina</span>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: '#e5e7eb' }} />

        {/* File name */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <BookOpen size={15} color="#9ca3af" />
          <span style={{ fontSize: 13.5, color: '#374151', fontWeight: 500, maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {file.name}
          </span>
          <span style={{ fontSize: 12, color: '#9ca3af' }}>({(file.size / 1024 / 1024).toFixed(1)} MB)</span>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Page nav */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <NavBtn onClick={() => goTo(currentPage - 1)} disabled={currentPage === 1}><ChevronLeft size={15} /></NavBtn>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#374151', fontWeight: 500 }}>
            <input
              type="number"
              value={currentPage}
              min={1}
              max={numPages}
              onChange={(e) => goTo(parseInt(e.target.value) || 1)}
              style={{
                width: 46, textAlign: 'center', padding: '4px 6px',
                border: '1px solid #e5e7eb', borderRadius: 7, fontSize: 13,
                fontWeight: 600, color: '#111827', outline: 'none',
              }}
            />
            <span style={{ color: '#9ca3af' }}>/ {numPages || '—'}</span>
          </div>
          <NavBtn onClick={() => goTo(currentPage + 1)} disabled={currentPage === numPages}><ChevronRight size={15} /></NavBtn>
        </div>

        {/* Zoom */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#f3f4f6', borderRadius: 8, padding: '2px 4px' }}>
          <NavBtn onClick={() => setScale(s => Math.max(0.5, s - 0.15))}><Minus size={13} /></NavBtn>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#374151', minWidth: 38, textAlign: 'center' }}>
            {Math.round(scale * 100)}%
          </span>
          <NavBtn onClick={() => setScale(s => Math.min(2.5, s + 0.15))}><Plus size={13} /></NavBtn>
        </div>

        {/* New Upload */}
        <button
          onClick={onReset}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px',
            background: '#f3f4f6', border: '1px solid #e5e7eb', borderRadius: 8,
            fontSize: 13, fontWeight: 600, color: '#374151', cursor: 'pointer',
            transition: 'all 0.15s',
          }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#e5e7eb')}
          onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#f3f4f6')}
        >
          <Upload size={14} /> New Upload
        </button>
      </header>

      {/* ── Body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* ── Page Navigation (Left Sidebar) ── */}
        <div style={{
          width: 220, flexShrink: 0, background: '#fff',
          borderRight: '1px solid #e5e7eb', overflowY: 'auto',
          display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ padding: '16px', fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.8, borderBottom: '1px solid #f0f0f0' }}>
            Document Pages
          </div>
          <div style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 16 }}>
            {numPages > 0 ? (
              <Document file={url}>
                {Array.from({ length: numPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => goTo(p)}
                    style={{
                      width: '100%', padding: 6, border: 'none', background: 'transparent',
                      cursor: 'pointer', display: 'flex', flexDirection: 'column',
                      alignItems: 'center', gap: 8, borderRadius: 8,
                      backgroundColor: p === currentPage ? '#e8f5f0' : 'transparent',
                      transition: 'background 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      if (p !== currentPage) (e.currentTarget as HTMLButtonElement).style.backgroundColor = '#f9fafb';
                    }}
                    onMouseLeave={(e) => {
                      if (p !== currentPage) (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                    }}
                  >
                    <div style={{ 
                      borderRadius: 4, overflow: 'hidden', 
                      boxShadow: p === currentPage ? '0 0 0 2px #0d3d2e' : '0 2px 8px rgba(0,0,0,0.1)',
                      background: '#fff', display: 'flex', justifyContent: 'center',
                      pointerEvents: 'none', width: '100%'
                    }}>
                      <Page 
                        pageNumber={p} 
                        width={170} 
                        renderTextLayer={false} 
                        renderAnnotationLayer={false} 
                      />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 600, color: p === currentPage ? '#0d3d2e' : '#9ca3af' }}>
                      {p}
                    </span>
                  </button>
                ))}
              </Document>
            ) : (
              <div style={{ padding: 20, fontSize: 12, color: '#9ca3af', textAlign: 'center' }}>
                Loading thumbnails...
              </div>
            )}
          </div>
        </div>

        {/* ── PDF Viewer (main) ── */}
        <div style={{
          flex: 1, overflowY: 'auto', display: 'flex',
          flexDirection: 'column', alignItems: 'center',
          padding: '32px 24px', gap: 0,
        }}>
          <Document
            file={url}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            loading={<LoadingSpinner label="Loading PDF…" />}
            error={<div style={{ color: '#dc2626', padding: 40, fontSize: 14 }}>Failed to load PDF.</div>}
          >
            <Page
              pageNumber={currentPage}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={false}
              customTextRenderer={textRenderer}
            />
          </Document>
        </div>

        {/* ── Analysis Panel (right) ── */}
        <div style={{
          width: 360, flexShrink: 0, background: '#fff',
          borderLeft: '1px solid #e5e7eb', display: 'flex',
          flexDirection: 'column', overflow: 'hidden',
        }}>
          {/* Panel Header */}
          <div style={{ padding: '16px 18px', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ fontWeight: 800, fontSize: 15, color: '#111827', marginBottom: 4 }}>
              Curriculum Analysis
            </div>
            <p style={{ fontSize: 12, color: '#9ca3af', lineHeight: 1.5 }}>
              Select pages and scan to identify outdated content and see current knowledge.
            </p>
          </div>

          {/* Scan Controls */}
          <div style={{ padding: '14px 18px', borderBottom: '1px solid #f0f0f0', background: '#fafafa' }}>
            {/* Scan mode selector */}
            <div style={{ fontSize: 11, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 10 }}>
              What to scan
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 14 }}>
              {([
                ['current', `Current Page (${currentPage})`],
                ['range', 'Custom Page Range'],
                ['all', `Full Document (${numPages} pages)`],
              ] as const).map(([val, label]) => (
                <label key={val} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="scanMode"
                    value={val}
                    checked={scanMode === val}
                    onChange={() => setScanMode(val)}
                    style={{ accentColor: '#0d3d2e', width: 15, height: 15 }}
                  />
                  <span style={{ fontSize: 13.5, color: '#374151', fontWeight: scanMode === val ? 600 : 400 }}>
                    {label}
                  </span>
                </label>
              ))}
            </div>

            {/* Custom range input */}
            {scanMode === 'range' && (
              <input
                type="text"
                placeholder="e.g. 1-5, 8, 12-15"
                value={selectedPages}
                onChange={(e) => setSelectedPages(e.target.value)}
                style={{
                  width: '100%', padding: '9px 12px', border: '1.5px solid #e5e7eb',
                  borderRadius: 9, fontSize: 13, outline: 'none', marginBottom: 12,
                  fontFamily: 'monospace', color: '#374151',
                }}
                onFocus={(e) => ((e.target as HTMLInputElement).style.borderColor = '#0d3d2e')}
                onBlur={(e) => ((e.target as HTMLInputElement).style.borderColor = '#e5e7eb')}
              />
            )}

            {/* Scan Button */}
            {!scanning ? (
              <button
                onClick={startScan}
                disabled={numPages === 0}
                style={{
                  width: '100%', padding: '12px', background: '#0d3d2e', color: '#fff',
                  border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700,
                  cursor: numPages === 0 ? 'not-allowed' : 'pointer', opacity: numPages === 0 ? 0.5 : 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'background 0.2s', boxShadow: '0 4px 12px rgba(13,61,46,0.25)',
                }}
                onMouseEnter={(e) => numPages > 0 && ((e.currentTarget as HTMLButtonElement).style.background = '#0a2e22')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#0d3d2e')}
              >
                <Scan size={16} />
                {findings.length > 0 ? 'Re-Scan' : scanLabel()}
              </button>
            ) : (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12.5, color: '#374151', fontWeight: 500 }}>
                    <RefreshCw size={13} color="#0d3d2e" className="spin" />
                    Analysing with AI…
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#0d3d2e' }}>{scanProgress}%</span>
                </div>
                <div style={{ height: 6, background: '#e5e7eb', borderRadius: 4 }}>
                  <div style={{
                    height: 6, background: 'linear-gradient(90deg, #0d3d2e, #1a6b52)',
                    borderRadius: 4, width: `${scanProgress}%`, transition: 'width 0.3s ease',
                  }} />
                </div>
              </div>
            )}
          </div>
          {/* Findings List */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '14px 18px' }}>
            {findings.length === 0 && !scanning ? (
              <div style={{ textAlign: 'center', paddingTop: 48, color: '#c4c9d4' }}>
                <Scan size={40} style={{ margin: '0 auto 12px', display: 'block', opacity: 0.4 }} />
                <p style={{ fontSize: 13.5, lineHeight: 1.6 }}>
                  Choose pages above and hit <strong style={{ color: '#0d3d2e' }}>Scan</strong> to get AI analysis.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Summary badge row */}
                {findings.length > 0 && (
                  <div style={{ display: 'flex', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                    {(['critical', 'outdated', 'aligned'] as const).map((t) => {
                      const count = findings.filter(f => f.type === t).length;
                      if (!count) return null;
                      const cfg = typeConfig[t];
                      return (
                        <div key={t} style={{
                          padding: '3px 10px', borderRadius: 20, fontSize: 11.5, fontWeight: 700,
                          background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
                        }}>
                          {count} {cfg.label}
                        </div>
                      );
                    })}
                  </div>
                )}

                {findings.map((f) => {
                  const cfg = typeConfig[f.type];
                  const Icon = cfg.icon;
                  const isOpen = activeFinding?.id === f.id;
                  return (
                    <div
                      key={f.id}
                      style={{
                        border: `1.5px solid ${isOpen ? cfg.color : cfg.border}`,
                        borderRadius: 12, overflow: 'hidden',
                        background: isOpen ? cfg.bg : '#fff',
                        transition: 'all 0.2s',
                      }}
                    >
                      <button
                        onClick={() => setActiveFinding(isOpen ? null : f)}
                        style={{
                          width: '100%', padding: '11px 13px', border: 'none',
                          background: 'transparent', cursor: 'pointer',
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Icon size={14} color={cfg.color} />
                          <span style={{ fontSize: 13, fontWeight: 700, color: '#111827' }}>{f.title}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 11, fontWeight: 600, color: cfg.color, background: cfg.bg, padding: '2px 8px', borderRadius: 20, border: `1px solid ${cfg.border}` }}>
                            {cfg.label}
                          </span>
                          <ChevronDown size={13} color="#9ca3af" style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                        </div>
                      </button>

                      {isOpen && (
                        <div style={{ padding: '0 13px 13px', borderTop: `1px solid ${cfg.border}` }} className="fade-in">
                          <div style={{ fontSize: 10.5, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', marginTop: 10, marginBottom: 5 }}>
                            In Your Textbook
                          </div>
                          <blockquote style={{
                            borderLeft: `3px solid ${cfg.color}`, paddingLeft: 10,
                            margin: '0 0 12px', fontSize: 12.5, color: '#374151',
                            fontStyle: 'italic', lineHeight: 1.65,
                          }}>
                            "{f.original}"
                          </blockquote>

                          {f.type !== 'aligned' && (
                            <>
                              <div style={{ fontSize: 10.5, fontWeight: 700, color: '#9ca3af', textTransform: 'uppercase', marginBottom: 5 }}>
                                Current Understanding
                              </div>
                              <div style={{
                                background: '#f8fffe', border: '1px solid #d1fae5',
                                borderRadius: 8, padding: '10px 12px',
                                fontSize: 12.5, color: '#1f2937', lineHeight: 1.65,
                              }}>
                                {f.updated}
                              </div>
                            </>
                          )}

                          {f.type === 'aligned' && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px', background: '#f0fdf4', borderRadius: 8, fontSize: 12.5, color: '#059669', fontWeight: 500 }}>
                              <CheckCircle size={14} />
                              This content is accurate and current.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Small helpers ─────────────────────────────────────────────────────────────
const NavBtn: React.FC<{ onClick: () => void; disabled?: boolean; children: React.ReactNode }> = ({ onClick, disabled, children }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      width: 30, height: 30, border: '1px solid #e5e7eb', borderRadius: 7,
      background: '#fff', cursor: disabled ? 'not-allowed' : 'pointer',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: disabled ? '#d1d5db' : '#374151', transition: 'background 0.15s',
    }}
    onMouseEnter={(e) => !disabled && ((e.currentTarget as HTMLButtonElement).style.background = '#f3f4f6')}
    onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#fff')}
  >
    {children}
  </button>
);

const LoadingSpinner: React.FC<{ label: string }> = ({ label }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, padding: 60 }}>
    <div style={{ width: 40, height: 40, border: '3px solid #e5e7eb', borderTopColor: '#0d3d2e', borderRadius: '50%' }} className="spin" />
    <p style={{ fontSize: 13.5, color: '#9ca3af' }}>{label}</p>
  </div>
);
