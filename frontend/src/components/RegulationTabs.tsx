import { useStore } from '../store'
import type { Regulation } from '../types'
import clsx from 'clsx'

const options: Regulation[] = ['GDPR', 'HIPAA', 'SOC2']

export function RegulationTabs() {
  const regulation = useStore((s) => s.regulation)
  const setRegulation = useStore((s) => s.setRegulation)

  return (
    <div className="flex bg-slate-900 rounded-md p-0.5 border border-slate-800">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => setRegulation(opt)}
          className={clsx(
            'px-4 py-1.5 text-sm rounded transition-colors',
            regulation === opt
              ? 'bg-sky-500/20 text-sky-300 font-medium'
              : 'text-slate-400 hover:text-slate-200',
          )}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}
