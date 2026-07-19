import { Check, Loader2, Circle } from 'lucide-react'
import clsx from 'clsx'
import { useStore } from '../store'
import type { TracePhase } from '../types'

const phaseLabel: Record<TracePhase, string> = {
  retrieve: 'Retrieving chunks',
  generate: 'Generating draft',
  reflect: 'Reflecting on answer',
}

export function TracePanel() {
  const trace = useStore((s) => s.trace)
  const isStreaming = useStore((s) => s.isStreaming)
  const answer = useStore((s) => s.answer)

  const showTrace = isStreaming || answer

  return (
    <div className="p-4 border-b border-slate-800 min-h-[140px]">
      <div className="text-xs uppercase tracking-wide text-slate-500 mb-3">Agent trace</div>
      {!showTrace ? (
        <div className="text-sm text-slate-500 italic">Awaiting question…</div>
      ) : (
        <ul className="space-y-2">
          {trace.map((step) => (
            <li key={step.phase} className="flex items-center gap-3 text-sm">
              <StatusIcon status={step.status} />
              <span
                className={clsx(
                  step.status === 'done' && 'text-slate-200',
                  step.status === 'active' && 'text-sky-300 font-medium',
                  step.status === 'pending' && 'text-slate-500',
                )}
              >
                {phaseLabel[step.phase]}
              </span>
              {step.detail && (
                <span className="text-xs text-slate-500 ml-auto">{step.detail}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: 'pending' | 'active' | 'done' }) {
  if (status === 'done') return <Check size={16} className="text-green-400" />
  if (status === 'active') return <Loader2 size={16} className="text-sky-400 animate-spin" />
  return <Circle size={16} className="text-slate-600" />
}
