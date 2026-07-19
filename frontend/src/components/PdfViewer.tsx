import { useEffect, useMemo, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/TextLayer.css'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import { FileText, ChevronLeft, ChevronRight } from 'lucide-react'
import { useStore } from '../store'

// Ship pdf.js worker from the same origin so no CORS/CDN dance is needed.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

const pdfOptions = {
  cMapUrl: 'https://unpkg.com/pdfjs-dist@4.8.69/cmaps/',
  cMapPacked: true,
}

export function PdfViewer() {
  const regulation = useStore((s) => s.regulation)
  const activePage = useStore((s) => s.activePage)
  const chunks = useStore((s) => s.chunks)

  const [numPages, setNumPages] = useState<number>(0)
  const [currentPage, setCurrentPage] = useState<number>(1)
  const pageContainerRef = useRef<HTMLDivElement | null>(null)

  const file = `/${regulation}.pdf`

  // Jump when store's activePage changes
  useEffect(() => {
    if (activePage) setCurrentPage(activePage)
  }, [activePage])

  // Reset when regulation swaps
  useEffect(() => {
    setCurrentPage(1)
    setNumPages(0)
  }, [regulation])

  // Substrings we want highlighted on the current page
  const highlightTerms = useMemo(
    () =>
      chunks
        .filter((c) => c.filename === `${regulation}.pdf` && c.page_number === currentPage)
        .map((c) => c.content.trim())
        .filter((s) => s.length > 15), // avoid noise
    [chunks, regulation, currentPage],
  )

  const customTextRenderer = useMemo(
    () =>
      ({ str }: { str: string }) => {
        if (!highlightTerms.length) return str
        let out = escapeHtml(str)
        for (const term of highlightTerms) {
          const escaped = escapeRegExp(term)
          const partial = matchPartial(out, term)
          if (partial) {
            out = out.replace(
              partial,
              `<mark class="pdf-highlight">${partial}</mark>`,
            )
          } else {
            out = out.replace(
              new RegExp(escaped, 'gi'),
              (m) => `<mark class="pdf-highlight">${m}</mark>`,
            )
          }
        }
        return out
      },
    [highlightTerms],
  )

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-slate-800 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 text-slate-300">
          <FileText size={14} />
          <span className="font-medium">{regulation}.pdf</span>
          <span className="text-slate-500">·</span>
          <span className="text-slate-500">
            Page {currentPage}
            {numPages > 0 ? ` of ${numPages}` : ''}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-30"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setCurrentPage((p) => Math.min(numPages || p, p + 1))}
            disabled={currentPage >= numPages}
            className="p-1 rounded hover:bg-slate-800 disabled:opacity-30"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div
        ref={pageContainerRef}
        className="flex-1 overflow-auto bg-slate-950 p-6 flex items-start justify-center"
      >
        <Document
          file={file}
          onLoadSuccess={({ numPages }) => setNumPages(numPages)}
          onLoadError={(e) => console.error('PDF load error:', e)}
          loading={
            <div className="text-slate-500 mt-16">Loading {regulation}.pdf…</div>
          }
          error={
            <div className="text-red-400 mt-16">
              Could not load {regulation}.pdf. Run <code>python scripts/build_public_pdfs.py</code>.
            </div>
          }
          options={pdfOptions}
        >
          {numPages > 0 && (
            <Page
              pageNumber={currentPage}
              width={700}
              renderAnnotationLayer={false}
              customTextRenderer={customTextRenderer}
              className="shadow-2xl"
            />
          )}
        </Document>
      </div>
    </div>
  )
}

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// If a chunk's phrase spans multiple text-layer strings, find the longest
// contiguous prefix/suffix overlap with this str so we still highlight
// the fragment on this line.
function matchPartial(str: string, term: string): string | null {
  const lower = str.toLowerCase()
  const t = term.toLowerCase()

  // Longest suffix of str that is a prefix of term
  for (let len = Math.min(str.length, term.length); len >= 8; len--) {
    const tail = lower.slice(str.length - len)
    if (t.startsWith(tail)) return str.slice(str.length - len)
  }
  // Longest prefix of str that is a suffix of term
  for (let len = Math.min(str.length, term.length); len >= 8; len--) {
    const head = lower.slice(0, len)
    if (t.endsWith(head)) return str.slice(0, len)
  }
  return null
}
