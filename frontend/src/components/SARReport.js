import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Download, AlertTriangle } from 'lucide-react';
export default function SARReport({ content }) {
    const download = () => {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `SAR_${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
    };
    return (_jsxs("div", { style: { borderTop: '1px solid #1e2d4a', background: '#0f172a', padding: 24, maxHeight: '40vh', overflowY: 'auto' }, children: [_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }, children: [_jsx(AlertTriangle, { size: 20, color: "#f59e0b" }), _jsx("span", { style: { fontSize: 14, fontWeight: 600, color: '#e2e8f0' }, children: "Investigation Report + SAR Draft" }), _jsxs("button", { onClick: download, style: { marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, background: '#1e2d4a', border: 'none', borderRadius: 6, padding: '6px 12px', color: '#94a3b8', fontSize: 12, cursor: 'pointer' }, children: [_jsx(Download, { size: 14 }), " Export"] })] }), _jsx("div", { style: { background: '#020817', borderRadius: 8, padding: 16, border: '1px solid #1e2d4a' }, children: _jsx("pre", { style: { fontSize: 12, color: '#94a3b8', lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }, children: content }) })] }));
}
