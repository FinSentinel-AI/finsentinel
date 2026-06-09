import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { CheckCircle, Circle, Loader } from 'lucide-react';
const STEPS = [
    { key: 'fraud_detector', label: 'Fraud Detection', desc: 'Velocity, patterns, anomalies' },
    { key: 'aml_analyst', label: 'AML Analysis', desc: 'Structuring, layering, round-tripping' },
    { key: 'risk_officer', label: 'Risk Scoring', desc: 'Composite score + watchlists' },
    { key: 'compliance_checker', label: 'Compliance Check', desc: 'BSA, FINRA, MiFID II, EU AI Act' },
    { key: 'report_generator', label: 'SAR Generation', desc: 'Report + audit trail to MongoDB' },
];
export default function InvestigationFlow({ completedAgents, activeAgent }) {
    return (_jsx("div", { style: { display: 'flex', alignItems: 'center', gap: 0, padding: '16px 24px', borderBottom: '1px solid #1e2d4a', overflowX: 'auto' }, children: STEPS.map((step, i) => {
            const done = completedAgents.includes(step.key);
            const active = activeAgent === step.key;
            return (_jsxs("div", { style: { display: 'flex', alignItems: 'center' }, children: [_jsxs("div", { style: { display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 120 }, children: [_jsx("div", { style: { marginBottom: 6 }, children: done ? _jsx(CheckCircle, { size: 20, color: "#10b981" }) :
                                    active ? _jsx(Loader, { size: 20, color: "#6366f1", style: { animation: 'spin 1s linear infinite' } }) :
                                        _jsx(Circle, { size: 20, color: "#374151" }) }), _jsx("span", { style: { fontSize: 11, fontWeight: 600, color: done ? '#10b981' : active ? '#6366f1' : '#475569', textAlign: 'center' }, children: step.label }), _jsx("span", { style: { fontSize: 10, color: '#374151', textAlign: 'center', marginTop: 2 }, children: step.desc })] }), i < STEPS.length - 1 && (_jsx("div", { style: { width: 40, height: 1, background: done ? '#10b981' : '#1e2d4a', margin: '0 4px', marginBottom: 20 } }))] }, step.key));
        }) }));
}
