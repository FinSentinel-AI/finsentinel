import { useState, useRef, useEffect } from 'react'
import { Shield, AlertTriangle, CheckCircle, Clock, Zap, Database, Network, TrendingUp } from 'lucide-react'
import InvestigationFlow from './components/InvestigationFlow'
import SARReport from './components/SARReport'

const AGENT_COLORS: Record<string, string> = {
  finsentinel_orchestrator: '#6366f1',
  fraud_detector: '#ef4444',
  aml_analyst: '#f59e0b',
  risk_officer: '#8b5cf6',
  compliance_checker: '#3b82f6',
  report_generator: '#10b981',
}

const AGENT_LABELS: Record<string, string> = {
  finsentinel_orchestrator: 'Orchestrator',
  fraud_detector: 'Fraud Detector',
  aml_analyst: 'AML Analyst',
  risk_officer: 'Risk Officer',
  compliance_checker: 'Compliance Checker',
  report_generator: 'Report Generator',
}

interface SimilarCase {
  transaction_id: string
  fraud_type?: string
  amount?: number
  description?: string
  score?: number
}

interface ImpactStats {
  flagged_amount: number
  investigation_time_s: number
  manual_time_s: number
  speedup_x: number
  est_cost_usd: number
  transactions_analyzed: number
  accounts_flagged: number
}

interface AgentEvent {
  type: string
  agent?: string
  content?: string
  message?: string
  timestamp: string
  cases?: SimilarCase[]
  stats?: ImpactStats
  investigation_id?: string
}

const PRESET_QUERIES = [
  'Investigate the last 24 hours of transactions for fraud and AML violations. Generate a SAR if needed.',
  'Find all structuring patterns in the past 48 hours and assess regulatory filing requirements.',
  'Run a full risk assessment on accounts with cross-border transactions over $10,000.',
  'Identify any round-tripping or layering patterns and generate a compliance report.',
]

export default function App() {
  const [query, setQuery] = useState(PRESET_QUERIES[0])
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const [finalReport, setFinalReport] = useState('')
  const [elapsedMs, setElapsedMs] = useState(0)
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([])
  const [impactStats, setImpactStats] = useState<ImpactStats | null>(null)
  const [auditEvent, setAuditEvent] = useState<AgentEvent | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const startRef = useRef<number>(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [events])

  const investigate = () => {
    if (running) return
    setEvents([])
    setFinalReport('')
    setSimilarCases([])
    setImpactStats(null)
    setAuditEvent(null)
    setDone(false)
    setRunning(true)
    startRef.current = Date.now()
    timerRef.current = setInterval(() => setElapsedMs(Date.now() - startRef.current), 100)

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}/ws/investigate`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => ws.send(JSON.stringify({ query, session_id: `sess_${Date.now()}` }))
    ws.onmessage = (e) => {
      const evt: AgentEvent = JSON.parse(e.data)
      if (evt.type === 'final') {
        setFinalReport(evt.content || '')
        setEvents(prev => [...prev, evt])
      } else if (evt.type === 'similar_cases') {
        setSimilarCases(evt.cases || [])
      } else if (evt.type === 'impact_stats') {
        setImpactStats(evt.stats || null)
      } else if (evt.type === 'audit_saved') {
        setAuditEvent(evt)
      } else if (evt.type === 'done') {
        setRunning(false)
        setDone(true)
        if (timerRef.current) clearInterval(timerRef.current)
      } else if (evt.type === 'error') {
        setEvents(prev => [...prev, evt])
        setRunning(false)
        if (timerRef.current) clearInterval(timerRef.current)
      } else {
        setEvents(prev => [...prev, evt])
      }
    }
    ws.onclose = () => { setRunning(false); if (timerRef.current) clearInterval(timerRef.current) }
  }

  const activeAgents = [...new Set(events.filter(e => e.agent).map(e => e.agent!))]
  const lastActiveAgent = events.filter(e => e.agent && e.type === 'agent_step').slice(-1)[0]?.agent ?? null
  const completedAgents = activeAgents.filter(a => a !== lastActiveAgent)

  return (
    <div style={{ minHeight: '100vh', background: '#0a0f1e', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{ padding: '20px 32px', borderBottom: '1px solid #1e2d4a', display: 'flex', alignItems: 'center', gap: 16 }}>
        <Shield size={32} color="#6366f1" />
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>FinSentinel</h1>
          <p style={{ fontSize: 12, color: '#64748b' }}>Autonomous Financial Crime Intelligence · Powered by Gemini + MongoDB Atlas</p>
        </div>
        {done && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontSize: 13 }}>
            <CheckCircle size={16} />
            Investigation complete in {(elapsedMs / 1000).toFixed(1)}s
          </div>
        )}
        {running && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8, color: '#f59e0b', fontSize: 13 }}>
            <Clock size={16} />
            {(elapsedMs / 1000).toFixed(1)}s elapsed
          </div>
        )}
      </header>

      <div style={{ display: 'flex', flex: 1, gap: 0 }}>
        {/* Left panel */}
        <div style={{ width: 380, borderRight: '1px solid #1e2d4a', display: 'flex', flexDirection: 'column', padding: 24, gap: 20 }}>
          <div>
            <label style={{ fontSize: 12, color: '#94a3b8', marginBottom: 8, display: 'block' }}>INVESTIGATION QUERY</label>
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              rows={4}
              style={{ width: '100%', background: '#0f172a', border: '1px solid #1e2d4a', borderRadius: 8, padding: '12px', color: '#e2e8f0', fontSize: 13, resize: 'vertical' }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: '#94a3b8', marginBottom: 8, display: 'block' }}>QUICK SCENARIOS</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {PRESET_QUERIES.map((q, i) => (
                <button key={i} onClick={() => setQuery(q)}
                  style={{ textAlign: 'left', background: query === q ? '#1e2d4a' : 'transparent', border: '1px solid #1e2d4a', borderRadius: 6, padding: '8px 12px', color: '#94a3b8', fontSize: 12, cursor: 'pointer' }}>
                  {q.slice(0, 60)}...
                </button>
              ))}
            </div>
          </div>
          <button onClick={investigate} disabled={running}
            style={{ background: running ? '#374151' : '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '14px', fontSize: 15, fontWeight: 600, cursor: running ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <Zap size={18} />
            {running ? 'Investigating...' : 'Launch Investigation'}
          </button>

          {/* Active agents */}
          {activeAgents.length > 0 && (
            <div>
              <label style={{ fontSize: 12, color: '#94a3b8', marginBottom: 8, display: 'block' }}>ACTIVE AGENTS</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {Object.entries(AGENT_LABELS).map(([key, label]) => (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: activeAgents.includes(key) ? 1 : 0.3 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: AGENT_COLORS[key] }} />
                    <span style={{ fontSize: 12, color: '#e2e8f0' }}>{label}</span>
                    {activeAgents.includes(key) && <CheckCircle size={12} color="#10b981" style={{ marginLeft: 'auto' }} />}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right panel */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* 5-step pipeline progress */}
          {(running || done) && (
            <InvestigationFlow completedAgents={completedAgents} activeAgent={running ? lastActiveAgent : null} />
          )}
          {/* Agent event log */}
          <div ref={logRef} style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 12, maxHeight: '60vh' }}>
            {events.length === 0 && !running && (
              <div style={{ textAlign: 'center', color: '#475569', marginTop: 60 }}>
                <Shield size={48} color="#1e2d4a" style={{ margin: '0 auto 16px' }} />
                <p style={{ fontSize: 16 }}>Select a scenario and launch an investigation</p>
                <p style={{ fontSize: 13, marginTop: 8 }}>5 specialist agents will investigate in real time</p>
              </div>
            )}
            {events.map((evt, i) => {
              if (evt.type === 'status') {
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#64748b', fontSize: 12 }}>
                    <Clock size={12} /> {evt.message}
                  </div>
                )
              }
              if (!evt.agent || !evt.content) return null
              const color = AGENT_COLORS[evt.agent] || '#94a3b8'
              const label = AGENT_LABELS[evt.agent] || evt.agent
              return (
                <div key={i} style={{ background: '#0f172a', border: `1px solid ${color}33`, borderRadius: 8, padding: '12px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                    <span style={{ fontSize: 11, fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: 1 }}>{label}</span>
                    <span style={{ fontSize: 11, color: '#475569', marginLeft: 'auto' }}>{new Date(evt.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{evt.content}</p>
                </div>
              )
            })}

            {/* Similar past fraud cases via Atlas $vectorSearch */}
            {similarCases.length > 0 && (
              <div style={{ background: '#0f172a', border: '1px solid #6366f133', borderRadius: 8, padding: '12px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <Network size={14} color="#6366f1" />
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#6366f1', textTransform: 'uppercase', letterSpacing: 1 }}>
                    Similar Past Cases — Atlas $vectorSearch
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {similarCases.map((c, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, color: '#cbd5e1', padding: '6px 8px', background: '#020817', borderRadius: 6 }}>
                      <span style={{ color: '#6366f1', fontFamily: 'monospace', fontSize: 11 }}>{c.transaction_id}</span>
                      <span style={{ color: '#94a3b8' }}>{c.fraud_type}</span>
                      <span style={{ marginLeft: 'auto', color: '#e2e8f0' }}>${(c.amount ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                      <span style={{ color: '#10b981', fontFamily: 'monospace', fontSize: 11 }}>sim {(c.score ?? 0).toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Impact stats strip */}
          {impactStats && (
            <div style={{ borderTop: '1px solid #1e2d4a', padding: '16px 24px', display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <TrendingUp size={16} color="#10b981" />
                <span style={{ fontSize: 13, color: '#e2e8f0' }}>
                  <strong>${impactStats.flagged_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
                  <span style={{ color: '#64748b' }}> flagged</span>
                </span>
              </div>
              <div style={{ fontSize: 13, color: '#e2e8f0' }}>
                <strong>{impactStats.investigation_time_s}s</strong>
                <span style={{ color: '#64748b' }}> vs 3 days </span>
                <span style={{ color: '#10b981' }}>({impactStats.speedup_x.toLocaleString()}x faster)</span>
              </div>
              <div style={{ fontSize: 13, color: '#e2e8f0' }}>
                <strong>{impactStats.transactions_analyzed.toLocaleString()}</strong>
                <span style={{ color: '#64748b' }}> transactions analyzed</span>
              </div>
              <div style={{ fontSize: 13, color: '#e2e8f0' }}>
                <strong>~${impactStats.est_cost_usd.toFixed(4)}</strong>
                <span style={{ color: '#64748b' }}> Gemini API cost</span>
              </div>
              {auditEvent && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', fontSize: 12, color: '#10b981' }}>
                  <Database size={14} />
                  Saved to MongoDB Atlas ({auditEvent.investigation_id})
                </div>
              )}
            </div>
          )}

          {/* SAR Report */}
          {finalReport && <SARReport content={finalReport} />}
        </div>
      </div>
    </div>
  )
}
