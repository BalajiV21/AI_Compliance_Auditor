import { useStore } from '../store'

export function AnswerBox() {
  const answer = useStore((s) => s.answer)
  const chunks = useStore((s) => s.chunks)
  const jumpToPage = useStore((s) => s.jumpToPage)

  if (!answer) {
    return (
      <div className="flex-1 p-4 text-sm text-slate-500 italic overflow-auto">
        The answer will appear here.
      </div>
    )
  }

  // Turn "[1]", "[2]" markers in the answer into clickable chips that jump the PDF.
  const parts = answer.split(/(\[\d+\])/g)

  return (
    <div className="flex-1 overflow-auto p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500 mb-3">Answer</div>
      <div className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed whitespace-pre-wrap">
        {parts.map((part, i) => {
          const m = part.match(/^\[(\d+)\]$/)
          if (!m) return <span key={i}>{part}</span>
          const idx = parseInt(m[1], 10) - 1
          const chunk = chunks[idx]
          if (!chunk) return <span key={i}>{part}</span>
          return (
            <button
              key={i}
              onClick={() => jumpToPage(chunk.page_number)}
              className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded bg-sky-500/20 text-sky-300 text-xs font-medium hover:bg-sky-500/30 border border-sky-500/40"
              title={`Jump to ${chunk.filename} · page ${chunk.page_number}`}
            >
              {part} p.{chunk.page_number}
            </button>
          )
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-slate-800">
        <div className="text-xs uppercase tracking-wide text-slate-500 mb-2">Sources</div>
        <ul className="space-y-1.5 text-xs text-slate-400">
          {chunks.map((c, i) => (
            <li key={i} className="flex justify-between gap-2">
              <span className="truncate">{c.citation}</span>
              <span className="text-slate-500 shrink-0">
                p.{c.page_number} · {(c.similarity_score * 100).toFixed(0)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
