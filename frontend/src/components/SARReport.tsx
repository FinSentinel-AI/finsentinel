import { FileText, Download, AlertTriangle } from 'lucide-react'

interface Props { content: string }

export default function SARReport({ content }: Props) {
  const download = () => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `SAR_${new Date().toISOString().split('T')[0]}.txt`
    a.click()
  }

  return (
    <div style={{ borderTop: '1px solid #1e2d4a', background: '#0f172a', padding: 24, maxHeight: '40vh', overflowY: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <AlertTriangle size={20} color="#f59e0b" />
        <span style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0' }}>Investigation Report + SAR Draft</span>
        <button onClick={download}
          style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, background: '#1e2d4a', border: 'none', borderRadius: 6, padding: '6px 12px', color: '#94a3b8', fontSize: 12, cursor: 'pointer' }}>
          <Download size={14} /> Export
        </button>
      </div>
      <div style={{ background: '#020817', borderRadius: 8, padding: 16, border: '1px solid #1e2d4a' }}>
        <pre style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
          {content}
        </pre>
      </div>
    </div>
  )
}
