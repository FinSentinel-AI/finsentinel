import { CheckCircle, Circle, Loader } from 'lucide-react'

const STEPS = [
  { key: 'fraud_detector', label: 'Fraud Detection', desc: 'Velocity, patterns, anomalies' },
  { key: 'aml_analyst', label: 'AML Analysis', desc: 'Structuring, layering, round-tripping' },
  { key: 'risk_officer', label: 'Risk Scoring', desc: 'Composite score + watchlists' },
  { key: 'compliance_checker', label: 'Compliance Check', desc: 'BSA, FINRA, MiFID II, EU AI Act' },
  { key: 'report_generator', label: 'SAR Generation', desc: 'Report + audit trail to MongoDB' },
]

interface Props {
  completedAgents: string[]
  activeAgent: string | null
}

export default function InvestigationFlow({ completedAgents, activeAgent }: Props) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, padding: '16px 24px', borderBottom: '1px solid #1e2d4a', overflowX: 'auto' }}>
      {STEPS.map((step, i) => {
        const done = completedAgents.includes(step.key)
        const active = activeAgent === step.key
        return (
          <div key={step.key} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 120 }}>
              <div style={{ marginBottom: 6 }}>
                {done ? <CheckCircle size={20} color="#10b981" /> :
                 active ? <Loader size={20} color="#6366f1" style={{ animation: 'spin 1s linear infinite' }} /> :
                 <Circle size={20} color="#374151" />}
              </div>
              <span style={{ fontSize: 11, fontWeight: 600, color: done ? '#10b981' : active ? '#6366f1' : '#475569', textAlign: 'center' }}>{step.label}</span>
              <span style={{ fontSize: 10, color: '#374151', textAlign: 'center', marginTop: 2 }}>{step.desc}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ width: 40, height: 1, background: done ? '#10b981' : '#1e2d4a', margin: '0 4px', marginBottom: 20 }} />
            )}
          </div>
        )
      })}
    </div>
  )
}
