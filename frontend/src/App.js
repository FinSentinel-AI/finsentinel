import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useRef, useEffect } from 'react';
import { Shield, CheckCircle, Clock, Zap } from 'lucide-react';
import InvestigationFlow from './components/InvestigationFlow';
import SARReport from './components/SARReport';
const AGENT_COLORS = {
    finsentinel_orchestrator: '#6366f1',
    fraud_detector: '#ef4444',
    aml_analyst: '#f59e0b',
    risk_officer: '#8b5cf6',
    compliance_checker: '#3b82f6',
    report_generator: '#10b981',
};
const AGENT_LABELS = {
    finsentinel_orchestrator: 'Orchestrator',
    fraud_detector: 'Fraud Detector',
    aml_analyst: 'AML Analyst',
    risk_officer: 'Risk Officer',
    compliance_checker: 'Compliance Checker',
    report_generator: 'Report Generator',
};
const PRESET_QUERIES = [
    'Investigate the last 24 hours of transactions for fraud and AML violations. Generate a SAR if needed.',
    'Find all structuring patterns in the past 48 hours and assess regulatory filing requirements.',
    'Run a full risk assessment on accounts with cross-border transactions over $10,000.',
    'Identify any round-tripping or layering patterns and generate a compliance report.',
];
export default function App() {
    const [query, setQuery] = useState(PRESET_QUERIES[0]);
    const [events, setEvents] = useState([]);
    const [running, setRunning] = useState(false);
    const [done, setDone] = useState(false);
    const [finalReport, setFinalReport] = useState('');
    const [elapsedMs, setElapsedMs] = useState(0);
    const wsRef = useRef(null);
    const startRef = useRef(0);
    const timerRef = useRef(null);
    const logRef = useRef(null);
    useEffect(() => {
        if (logRef.current)
            logRef.current.scrollTop = logRef.current.scrollHeight;
    }, [events]);
    const investigate = () => {
        if (running)
            return;
        setEvents([]);
        setFinalReport('');
        setDone(false);
        setRunning(true);
        startRef.current = Date.now();
        timerRef.current = setInterval(() => setElapsedMs(Date.now() - startRef.current), 100);
        const wsUrl = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/investigate`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onopen = () => ws.send(JSON.stringify({ query, session_id: `sess_${Date.now()}` }));
        ws.onmessage = (e) => {
            const evt = JSON.parse(e.data);
            if (evt.type === 'final') {
                setFinalReport(evt.content || '');
                setEvents(prev => [...prev, evt]);
            }
            else if (evt.type === 'done') {
                setRunning(false);
                setDone(true);
                if (timerRef.current)
                    clearInterval(timerRef.current);
            }
            else if (evt.type === 'error') {
                setEvents(prev => [...prev, evt]);
                setRunning(false);
                if (timerRef.current)
                    clearInterval(timerRef.current);
            }
            else {
                setEvents(prev => [...prev, evt]);
            }
        };
        ws.onclose = () => { setRunning(false); if (timerRef.current)
            clearInterval(timerRef.current); };
    };
    const activeAgents = [...new Set(events.filter(e => e.agent).map(e => e.agent))];
    const lastActiveAgent = events.filter(e => e.agent && e.type === 'agent_step').slice(-1)[0]?.agent ?? null;
    const completedAgents = activeAgents.filter(a => a !== lastActiveAgent);
    return (_jsxs("div", { style: { minHeight: '100vh', background: '#0a0f1e', display: 'flex', flexDirection: 'column' }, children: [_jsxs("header", { style: { padding: '20px 32px', borderBottom: '1px solid #1e2d4a', display: 'flex', alignItems: 'center', gap: 16 }, children: [_jsx(Shield, { size: 32, color: "#6366f1" }), _jsxs("div", { children: [_jsx("h1", { style: { fontSize: 22, fontWeight: 700, color: '#e2e8f0' }, children: "FinSentinel" }), _jsx("p", { style: { fontSize: 12, color: '#64748b' }, children: "Autonomous Financial Crime Intelligence \u00B7 Powered by Gemini + MongoDB Atlas" })] }), done && (_jsxs("div", { style: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', fontSize: 13 }, children: [_jsx(CheckCircle, { size: 16 }), "Investigation complete in ", (elapsedMs / 1000).toFixed(1), "s"] })), running && (_jsxs("div", { style: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8, color: '#f59e0b', fontSize: 13 }, children: [_jsx(Clock, { size: 16 }), (elapsedMs / 1000).toFixed(1), "s elapsed"] }))] }), _jsxs("div", { style: { display: 'flex', flex: 1, gap: 0 }, children: [_jsxs("div", { style: { width: 380, borderRight: '1px solid #1e2d4a', display: 'flex', flexDirection: 'column', padding: 24, gap: 20 }, children: [_jsxs("div", { children: [_jsx("label", { style: { fontSize: 12, color: '#94a3b8', marginBottom: 8, display: 'block' }, children: "INVESTIGATION QUERY" }), _jsx("textarea", { value: query, onChange: e => setQuery(e.target.value), rows: 4, style: { width: '100%', background: '#0f172a', border: '1px solid #1e2d4a', borderRadius: 8, padding: '12px', color: '#e2e8f0', fontSize: 13, resize: 'vertical' } })] }), _jsxs("div", { children: [_jsx("label", { style: { fontSize: 12, color: '#94a3b8', marginBottom: 8, display: 'block' }, children: "QUICK SCENARIOS" }), _jsx("div", { style: { display: 'flex', flexDirection: 'column', gap: 8 }, children: PRESET_QUERIES.map((q, i) => (_jsxs("button", { onClick: () => setQuery(q), style: { textAlign: 'left', background: query === q ? '#1e2d4a' : 'transparent', border: '1px solid #1e2d4a', borderRadius: 6, padding: '8px 12px', color: '#94a3b8', fontSize: 12, cursor: 'pointer' }, children: [q.slice(0, 60), "..."] }, i))) })] }), _jsxs("button", { onClick: investigate, disabled: running, style: { background: running ? '#374151' : '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '14px', fontSize: 15, fontWeight: 600, cursor: running ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }, children: [_jsx(Zap, { size: 18 }), running ? 'Investigating...' : 'Launch Investigation'] }), activeAgents.length > 0 && (_jsxs("div", { children: [_jsx("label", { style: { fontSize: 12, color: '#94a3b8', marginBottom: 8, display: 'block' }, children: "ACTIVE AGENTS" }), _jsx("div", { style: { display: 'flex', flexDirection: 'column', gap: 6 }, children: Object.entries(AGENT_LABELS).map(([key, label]) => (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 8, opacity: activeAgents.includes(key) ? 1 : 0.3 }, children: [_jsx("div", { style: { width: 8, height: 8, borderRadius: '50%', background: AGENT_COLORS[key] } }), _jsx("span", { style: { fontSize: 12, color: '#e2e8f0' }, children: label }), activeAgents.includes(key) && _jsx(CheckCircle, { size: 12, color: "#10b981", style: { marginLeft: 'auto' } })] }, key))) })] }))] }), _jsxs("div", { style: { flex: 1, display: 'flex', flexDirection: 'column' }, children: [(running || done) && (_jsx(InvestigationFlow, { completedAgents: completedAgents, activeAgent: running ? lastActiveAgent : null })), _jsxs("div", { ref: logRef, style: { flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 12, maxHeight: '60vh' }, children: [events.length === 0 && !running && (_jsxs("div", { style: { textAlign: 'center', color: '#475569', marginTop: 60 }, children: [_jsx(Shield, { size: 48, color: "#1e2d4a", style: { margin: '0 auto 16px' } }), _jsx("p", { style: { fontSize: 16 }, children: "Select a scenario and launch an investigation" }), _jsx("p", { style: { fontSize: 13, marginTop: 8 }, children: "5 specialist agents will investigate in real time" })] })), events.map((evt, i) => {
                                        if (evt.type === 'status') {
                                            return (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 8, color: '#64748b', fontSize: 12 }, children: [_jsx(Clock, { size: 12 }), " ", evt.message] }, i));
                                        }
                                        if (!evt.agent || !evt.content)
                                            return null;
                                        const color = AGENT_COLORS[evt.agent] || '#94a3b8';
                                        const label = AGENT_LABELS[evt.agent] || evt.agent;
                                        return (_jsxs("div", { style: { background: '#0f172a', border: `1px solid ${color}33`, borderRadius: 8, padding: '12px 16px' }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }, children: [_jsx("div", { style: { width: 8, height: 8, borderRadius: '50%', background: color } }), _jsx("span", { style: { fontSize: 11, fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: 1 }, children: label }), _jsx("span", { style: { fontSize: 11, color: '#475569', marginLeft: 'auto' }, children: new Date(evt.timestamp).toLocaleTimeString() })] }), _jsx("p", { style: { fontSize: 13, color: '#cbd5e1', lineHeight: 1.6, whiteSpace: 'pre-wrap' }, children: evt.content })] }, i));
                                    })] }), finalReport && _jsx(SARReport, { content: finalReport })] })] })] }));
}
