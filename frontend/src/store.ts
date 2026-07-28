import { create } from 'zustand'
import type { Regulation, RetrievedChunk, StreamEvent, TraceStep } from './types'
import { mockEventStream } from './mockStream'
import { realEventStream } from './realStream'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const eventStream = USE_MOCK ? mockEventStream : realEventStream

interface AppState {
  regulation: Regulation
  query: string
  isStreaming: boolean
  trace: TraceStep[]
  chunks: RetrievedChunk[]
  answer: string
  iterations: number
  reflection: string
  activePage: number | null
  error: string | null

  setRegulation: (r: Regulation) => void
  setQuery: (q: string) => void
  jumpToPage: (page: number) => void
  runQuery: () => Promise<void>
  reset: () => void
}

const emptyTrace = (): TraceStep[] => [
  { phase: 'retrieve', status: 'pending' },
  { phase: 'generate', status: 'pending' },
  { phase: 'reflect', status: 'pending' },
]

export const useStore = create<AppState>((set, get) => ({
  regulation: 'GDPR',
  query: '',
  isStreaming: false,
  trace: emptyTrace(),
  chunks: [],
  answer: '',
  iterations: 0,
  reflection: '',
  activePage: null,
  error: null,

  setRegulation: (r) => set({ regulation: r }),
  setQuery: (q) => set({ query: q }),
  jumpToPage: (page) => set({ activePage: page }),

  reset: () =>
    set({
      isStreaming: false,
      trace: emptyTrace(),
      chunks: [],
      answer: '',
      iterations: 0,
      reflection: '',
      error: null,
    }),

  runQuery: async () => {
    const q = get().query.trim()
    if (!q || get().isStreaming) return

    get().reset()
    set({ isStreaming: true, trace: [{ phase: 'retrieve', status: 'active' }, { phase: 'generate', status: 'pending' }, { phase: 'reflect', status: 'pending' }] })

    try {
      for await (const evt of eventStream(q)) {
        applyEvent(evt, set, get)
      }
    } catch (e: any) {
      set({ error: e?.message ?? 'Unknown error' })
    } finally {
      set({ isStreaming: false })
    }
  },
}))

function applyEvent(
  evt: StreamEvent,
  set: (partial: Partial<AppState>) => void,
  get: () => AppState,
) {
  const trace = [...get().trace]
  const mark = (phase: 'retrieve' | 'generate' | 'reflect', status: TraceStep['status'], detail?: string) => {
    const i = trace.findIndex((s) => s.phase === phase)
    if (i >= 0) trace[i] = { ...trace[i], status, detail }
  }

  switch (evt.event) {
    case 'retrieved':
      mark('retrieve', 'done', `${evt.data.count} chunks`)
      mark('generate', 'active')
      set({ trace, chunks: evt.data.chunks })
      break
    case 'generating':
      mark('generate', 'done')
      mark('reflect', 'active')
      set({ trace })
      break
    case 'reflecting':
      mark(
        'reflect',
        'done',
        evt.data.needs_retry ? `iter ${evt.data.iteration} — retry` : `iter ${evt.data.iteration}`,
      )
      set({ trace, reflection: evt.data.reflection, iterations: evt.data.iteration })
      break
    case 'answer':
      set({
        answer: evt.data.text,
        iterations: evt.data.iterations,
        reflection: evt.data.reflection,
        chunks: evt.data.sources,
      })
      break
    case 'error':
      set({ error: evt.data.error })
      break
    case 'done':
    case 'start':
      break
  }
}
