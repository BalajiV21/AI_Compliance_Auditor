// Event shapes emitted by POST /query/stream (Server-Sent Events).
// Keep these in lockstep with src/api/main.py :: event_generator().

export type Regulation = 'GDPR' | 'HIPAA' | 'SOC2'

export interface RetrievedChunk {
  content: string
  citation: string
  similarity_score: number
  filename: string
  document_type: string
  page_number: number
  section: string
}

export type StreamEvent =
  | { event: 'start'; data: { session_id: string; query: string } }
  | { event: 'retrieved'; data: { count: number; chunks: RetrievedChunk[] } }
  | { event: 'generating'; data: { has_answer: boolean } }
  | { event: 'reflecting'; data: { iteration: number; reflection: string; needs_retry: boolean } }
  | {
      event: 'answer'
      data: {
        text: string
        sources: RetrievedChunk[]
        iterations: number
        reflection: string
        session_id: string
        timestamp: string
      }
    }
  | { event: 'done'; data: Record<string, never> }
  | { event: 'error'; data: { error: string } }

export type TracePhase = 'retrieve' | 'generate' | 'reflect'
export type PhaseStatus = 'pending' | 'active' | 'done'

export interface TraceStep {
  phase: TracePhase
  status: PhaseStatus
  detail?: string
}
