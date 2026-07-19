import { useStore } from '../store'
import { Send } from 'lucide-react'

export function QuestionInput() {
  const query = useStore((s) => s.query)
  const setQuery = useStore((s) => s.setQuery)
  const runQuery = useStore((s) => s.runQuery)
  const isStreaming = useStore((s) => s.isStreaming)

  const submit = () => {
    if (!isStreaming) runQuery()
  }

  return (
    <div className="p-4 border-b border-slate-800">
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Ask about GDPR Article 17…"
          className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          disabled={isStreaming}
        />
        <button
          onClick={submit}
          disabled={isStreaming || !query.trim()}
          className="px-3 rounded bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-900 font-medium flex items-center gap-1.5"
        >
          <Send size={14} />
          Ask
        </button>
      </div>
    </div>
  )
}
