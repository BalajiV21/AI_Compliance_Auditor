import { RegulationTabs } from './components/RegulationTabs'
import { PdfViewer } from './components/PdfViewer'
import { QuestionInput } from './components/QuestionInput'
import { TracePanel } from './components/TracePanel'
import { AnswerBox } from './components/AnswerBox'

export default function App() {
  return (
    <div className="h-screen w-screen flex flex-col bg-[#0b1220] text-slate-200">
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-gradient-to-br from-sky-400 to-indigo-500" />
          <div>
            <div className="font-semibold">Agentic Compliance Auditor</div>
            <div className="text-xs text-slate-400">Live workflow trace · Grounded citations</div>
          </div>
        </div>
        <RegulationTabs />
      </header>

      <div className="flex flex-1 min-h-0">
        <section className="flex-1 border-r border-slate-800 min-w-0">
          <PdfViewer />
        </section>

        <aside className="w-[520px] flex flex-col min-h-0">
          <QuestionInput />
          <TracePanel />
          <AnswerBox />
        </aside>
      </div>
    </div>
  )
}
