import React, { useCallback, useRef, useState } from 'react';
import { Upload, FileText, GraduationCap, Sparkles, BookOpen, Zap } from 'lucide-react';
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface UploadViewProps {
  onFileLoaded: (file: File, url: string) => void;
}

export const UploadView: React.FC<UploadViewProps> = ({ onFileLoaded }) => {
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file || file.type !== 'application/pdf') {
      alert('Please upload a valid PDF file.');
      return;
    }
    setLoading(true);
    
    try {
      // 1. Create a URL for the file to read it with pdfjs
      const url = URL.createObjectURL(file);
      
      // 2. Extract text using pdfjs (optional now since no backend, but kept as requested before)
      const doc = await pdfjs.getDocument(url).promise;
      const numPages = doc.numPages;
      let extractedText = "";
      
      for (let i = 1; i <= numPages; i++) {
        const page = await doc.getPage(i);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map((item: any) => item.str).join(" ");
        extractedText += `--- Page ${i} ---\n${pageText}\n\n`;
      }

      // 3. Send extracted text as JSON
      const response = await fetch('http://127.0.0.1:5000/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: file.name,
          text: extractedText,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send text to the backend.');
      }

      onFileLoaded(file, url);
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to upload file to the backend.');
      setLoading(false);
    }
  }, [onFileLoaded]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(160deg, #f0fdf4 0%, #f8f9fa 40%, #eff6ff 100%)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 24px',
    }}>
      {/* Logo */}
      <div className="fade-in" style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 48 }}>
        <div style={{
          width: 48, height: 48, background: '#0d3d2e', borderRadius: 12,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(13,61,46,0.3)',
        }}>
          <GraduationCap size={26} color="#fff" strokeWidth={2} />
        </div>
        <div>
          <div style={{ fontSize: 22, fontWeight: 900, color: '#0d3d2e', letterSpacing: -0.5 }}>Lumina</div>
          <div style={{ fontSize: 12, color: '#6b7280', fontWeight: 500, letterSpacing: 0.2 }}>AI Curriculum Companion</div>
        </div>
      </div>

      {/* Heading */}
      <div className="fade-in" style={{ textAlign: 'center', marginBottom: 48, animationDelay: '0.05s' }}>
        <h1 style={{ fontSize: 38, fontWeight: 900, color: '#111827', letterSpacing: -1, lineHeight: 1.2, marginBottom: 14 }}>
          Upload your textbook.<br />
          <span style={{ color: '#0d3d2e' }}>Discover what's changed.</span>
        </h1>
        <p style={{ fontSize: 16, color: '#6b7280', maxWidth: 480, margin: '0 auto', lineHeight: 1.65 }}>
          Drop in any curriculum PDF and Lumina will help you read through it, identify outdated content, and show you the current understanding page by page.
        </p>
      </div>

      {/* Upload Zone */}
      <div
        className="fade-in"
        style={{ animationDelay: '0.1s', width: '100%', maxWidth: 560 }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !loading && fileRef.current?.click()}
      >
        <input ref={fileRef} type="file" accept=".pdf" onChange={handleChange} style={{ display: 'none' }} />
        <div style={{
          border: `2.5px dashed ${dragOver ? '#0d3d2e' : '#cbd5e1'}`,
          borderRadius: 20,
          padding: '56px 40px',
          textAlign: 'center',
          background: dragOver ? 'rgba(13,61,46,0.04)' : '#fff',
          cursor: loading ? 'wait' : 'pointer',
          transition: 'all 0.25s ease',
          boxShadow: dragOver ? '0 0 0 4px rgba(13,61,46,0.08)' : '0 4px 24px rgba(0,0,0,0.06)',
        }}>
          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
              <div style={{
                width: 52, height: 52, borderRadius: '50%',
                border: '3px solid #e5e7eb', borderTopColor: '#0d3d2e',
              }} className="spin" />
              <p style={{ fontSize: 15, fontWeight: 600, color: '#0d3d2e' }}>Opening your PDF…</p>
            </div>
          ) : (
            <>
              <div style={{
                width: 70, height: 70, borderRadius: '50%',
                background: dragOver ? '#e8f5f0' : '#f3f4f6',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 20px',
                transition: 'background 0.2s',
              }}>
                {dragOver
                  ? <FileText size={32} color="#0d3d2e" />
                  : <Upload size={32} color="#9ca3af" />
                }
              </div>
              <h2 style={{ fontSize: 19, fontWeight: 700, color: '#111827', marginBottom: 8 }}>
                {dragOver ? 'Drop it here!' : 'Drag & drop your PDF'}
              </h2>
              <p style={{ fontSize: 14, color: '#9ca3af', marginBottom: 28 }}>
                Supports PDF files up to 50 MB
              </p>
              <button style={{
                padding: '13px 36px',
                background: '#0d3d2e',
                color: '#fff',
                border: 'none',
                borderRadius: 12,
                fontSize: 15,
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 4px 14px rgba(13,61,46,0.3)',
                transition: 'all 0.2s',
              }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#0a2e22')}
                onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.background = '#0d3d2e')}
              >
                Browse Files
              </button>
            </>
          )}
        </div>
      </div>

      {/* Feature Hints */}
      <div className="fade-in" style={{
        display: 'flex', gap: 24, marginTop: 48, flexWrap: 'wrap', justifyContent: 'center',
        animationDelay: '0.15s',
      }}>
        {[
          { icon: BookOpen, label: 'Page-by-page reading', color: '#0d3d2e' },
          { icon: Zap, label: 'AI-powered analysis', color: '#d97706' },
          { icon: Sparkles, label: 'Outdated content flagged', color: '#7c3aed' },
        ].map(({ icon: Icon, label, color }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Icon size={16} color={color} />
            </div>
            <span style={{ fontSize: 13.5, color: '#6b7280', fontWeight: 500 }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
