// Real SSE client that talks to the deployed FastAPI backend at /api/query/stream.
// Used when VITE_USE_MOCK is not "true".
//
// Path is relative (/api/...) so nginx can reverse-proxy it to localhost:8000
// on the same origin — no CORS handling needed in production.

import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { StreamEvent } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

export async function* realEventStream(query: string): AsyncGenerator<StreamEvent> {
  // fetchEventSource pushes events into a callback; adapt it to an async iterator via a queue.
  const queue: StreamEvent[] = []
  let done = false
  let err: unknown = null
  let notify: (() => void) | null = null

  const wake = () => {
    const n = notify
    notify = null
    n?.()
  }

  const controller = new AbortController()

  fetchEventSource(`${API_BASE}/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
    signal: controller.signal,
    openWhenHidden: true,
    onmessage(msg) {
      if (!msg.event) return
      try {
        const data = msg.data ? JSON.parse(msg.data) : {}
        queue.push({ event: msg.event, data } as StreamEvent)
        wake()
      } catch (e) {
        err = e
        done = true
        wake()
      }
    },
    onerror(e) {
      err = e
      done = true
      wake()
      throw e // stop retries
    },
    onclose() {
      done = true
      wake()
    },
  }).catch((e) => {
    err = e
    done = true
    wake()
  })

  try {
    while (true) {
      if (queue.length) {
        yield queue.shift()!
        continue
      }
      if (done) {
        if (err) throw err
        return
      }
      await new Promise<void>((resolve) => {
        notify = resolve
      })
    }
  } finally {
    controller.abort()
  }
}
