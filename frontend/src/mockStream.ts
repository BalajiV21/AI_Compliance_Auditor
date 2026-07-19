// Fake SSE producer for local development while the backend has no data.
// Yields events on a timer to mimic real agent latency.
// Chunk `content` uses exact substrings that appear in frontend/public/GDPR.pdf
// so the text-layer highlighter can find and mark them.

import type { StreamEvent } from './types'

const sampleChunks = [
  {
    content:
      "The data subject shall have the right to obtain from the controller the erasure of personal data concerning him or her without undue delay",
    citation: '[1] GDPR - Article 17 (Source: GDPR.pdf)',
    similarity_score: 0.92,
    filename: 'GDPR.pdf',
    document_type: 'GDPR',
    page_number: 2,
    section: "Article 17 - Right to erasure ('right to be forgotten')",
  },
  {
    content:
      "processed in a manner that ensures appropriate security of the personal data",
    citation: '[2] GDPR - Article 5(f) (Source: GDPR.pdf)',
    similarity_score: 0.81,
    filename: 'GDPR.pdf',
    document_type: 'GDPR',
    page_number: 1,
    section: 'Article 5 - Principles relating to processing of personal data',
  },
  {
    content:
      "Where the controller has made the personal data public and is obliged to erase the personal data",
    citation: '[3] GDPR - Article 17(2) (Source: GDPR.pdf)',
    similarity_score: 0.77,
    filename: 'GDPR.pdf',
    document_type: 'GDPR',
    page_number: 2,
    section: "Article 17 - Right to erasure ('right to be forgotten')",
  },
]

const sampleAnswer = `Under **GDPR Article 17** [1], data subjects have the right to obtain erasure of their personal data without undue delay when it is no longer necessary for the original purpose.

The security principle in Article 5(f) [2] requires controllers to protect personal data with appropriate safeguards throughout processing.

When data has been made public, the controller must take reasonable steps to inform downstream controllers of the erasure request [3].`

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function* mockEventStream(query: string): AsyncGenerator<StreamEvent> {
  yield { event: 'start', data: { session_id: 'mock-session', query } }
  await delay(400)

  yield { event: 'retrieved', data: { count: sampleChunks.length, chunks: sampleChunks } }
  await delay(900)

  yield { event: 'generating', data: { has_answer: true } }
  await delay(700)

  yield {
    event: 'reflecting',
    data: { iteration: 1, reflection: 'Answer is grounded and cited. No retry needed.', needs_retry: false },
  }
  await delay(400)

  yield {
    event: 'answer',
    data: {
      text: sampleAnswer,
      sources: sampleChunks,
      iterations: 1,
      reflection: 'Answer is grounded and cited. No retry needed.',
      session_id: 'mock-session',
      timestamp: new Date().toISOString(),
    },
  }

  yield { event: 'done', data: {} }
}
