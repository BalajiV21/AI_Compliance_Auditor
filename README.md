# Agentic Compliance Auditor

> An AI compliance assistant that audits documents against GDPR, HIPAA, and SOC2 — using autonomous agents that plan, retrieve, reason, and self-check before returning a cited answer.

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![LangGraph](https://img.shields.io/badge/LangGraph-agentic-orange?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-REST-green?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector--db-purple?style=flat-square)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)

---

## Why I Built This

Compliance teams spend hours manually cross-referencing regulatory documents to answer questions like *"Do our data retention policies meet GDPR Article 17?"* or *"What exactly does HIPAA require for PHI access logs?"*. The problem isn't just time — it's that generic LLMs hallucinate regulatory details and never cite their sources, which makes them useless in a compliance context where every claim needs to be traceable.

I wanted to build something that could actually reason through these questions — not just retrieve text, but plan a search strategy, pull the right chunks, generate an answer, and then check its own work before responding.

## What It Does

You ask a compliance question. The system:

1. Searches your regulatory documents using both semantic and keyword retrieval
2. Constructs an answer grounded in what it actually found
3. Self-critiques the response — if citations are missing or the answer is vague, it tries again
4. Returns the final answer with specific article/section references

Everything except the LLM call runs locally. Documents, embeddings, and session state stay on your machine — only the composed prompt is sent to OpenAI for generation.

---

## Live Demo

🔗 **[http://3.146.120.158/](http://3.146.120.158/)** — hosted on AWS EC2

## Screenshots

![Agentic Compliance Auditor UI](img/Screenshot%202026-08-13%20005103.png)

*Left: the regulation PDF (HIPAA on page 3 of 8). Right: the live agent trace (retrieve → generate → reflect), the generated answer, and clickable citation chips that jump the PDF viewer to the source passage. Regulation tabs (GDPR / HIPAA / SOC2) in the top-right switch both the PDF and the retrieval scope.*

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent Framework | LangGraph | State machine for multi-step reasoning and self-reflection loops |
| LLM | OpenAI gpt-4o-mini | Fast, cheap, strong reasoning — ~$0.15 per 1M input tokens |
| Embeddings | OpenAI text-embedding-3-small | 1536-dim vectors, ~$0.02 per 1M tokens |
| Vector DB | ChromaDB | Semantic document search and storage |
| Session Memory | Redis (with in-memory fallback) | Conversation context across queries |
| API | FastAPI + sse-starlette | REST + Server-Sent Events streaming |
| Frontend | React + Vite + TypeScript, Tailwind CSS | Split-screen PDF viewer + live workflow trace |
| PDF viewer | react-pdf (pdf.js) | Renders regulation PDFs with text-layer highlighting for cited passages |
| State | Zustand | Small global store shared by frontend components |
| Reverse proxy | nginx | Serves the built React app + reverse-proxies /api/* to FastAPI |
| Hosting | AWS EC2 (t3.medium, Amazon Linux 2023) | Single-instance deploy, systemd-managed services |
| Evaluation | RAGAS | Measuring faithfulness, recall, and citation accuracy |

### Supported Regulations

- **GDPR** — General Data Protection Regulation
- **HIPAA** — Health Insurance Portability and Accountability Act
- **SOC2** — Service Organization Control 2
- Extensible to any PDF-based regulatory framework

---

## Architecture

The agent runs three sequential steps — retrieve, generate, reflect — inside a LangGraph state machine. Reflection can loop back to retrieve if the answer isn't grounded.

```
User query
    │  (HTTP POST /query  { query, session_id })
    ▼
FastAPI endpoint
    │
    ▼
ComplianceAgent  ── LangGraph StateGraph ──────────────────────┐
                                                               │
  Step 1. Retrieve                                             │
    │                                                          │
    │  query text                                              │
    ▼                                                          │
  HybridRetriever                                              │
    ├── Semantic search  →  ChromaDB                           │
    │    (query embedded via OpenAI                            │
    │     text-embedding-3-small, 1536-dim)                    │
    └── Keyword search   →  BM25 over chunk text               │
    │                                                          │
    │  top-k chunks + similarity scores + citations            │
    ▼                                                          │
                                                               │
  Step 2. Generate                                             │
    │                                                          │
    │  system prompt + user query + retrieved chunks           │
    ▼                                                          │
  OpenAI gpt-4o-mini (API call)                                │
    │                                                          │
    │  draft answer                                            │
    ▼                                                          │
                                                               │
  Step 3. Reflect  (conditional edge, optional)                │
    │                                                          │
    │  draft answer + retrieved chunks                         │
    ▼                                                          │
  Reflection LLM call  ── grounded + properly cited? ──────────┤
    │                                                          │
    │  yes → finalize           no → loop back to Step 1 ──────┘
    ▼                          (max N iterations, default 3)
Final answer + citations
    │
    └──►  Redis   (session history keyed by session_id; in-memory fallback if Redis is down)
    │
    ▼
HTTP response  { answer, sources[], citations[], iterations }
```

A few things the diagram makes explicit that are worth calling out:

- **Embeddings are a library call, not a service.** `sentence-transformers` runs in-process inside the retriever — there's no separate embedding server to deploy.
- **The agent is sequential, not parallel.** Retrieve completes before generate starts; generate completes before reflect starts. The arrows are data, not concurrent paths.
- **Reflection is what makes it "agentic".** A plain RAG pipeline stops at Step 2. The reflection node re-checks grounding and can send the state back to Step 1 with a refined query. This is the loop that LangGraph's conditional edges enable.
- **Hybrid retrieval** means every query hits both ChromaDB (semantic) and a BM25 scorer (keyword). Results are merged and reranked before being handed to the LLM — this is what makes article-number queries like "GDPR Article 17" land on the right chunk.

### Design Decisions

**Why LangGraph instead of plain LangChain agents?**
LangChain's older agent API doesn't give you fine-grained control over the execution loop. LangGraph lets you define explicit state transitions and conditional edges — which was necessary for the self-reflection loop. Without it, the agent either always reflects or never does. With LangGraph, the reflection step only fires when the answer fails a quality check.

**Why hybrid retrieval?**
Semantic search alone wasn't good enough. When someone asks about "Article 17 of GDPR", pure vector similarity often surfaces broadly related content about data rights — not the specific article. BM25 keyword matching catches exact article references that semantic search misses. Running both and reranking the combined results gave noticeably better precision on targeted queries.

**Why Redis for session memory?**
Fast key-value lookup for conversation history per session ID. The system degrades gracefully if Redis isn't running — it falls back to in-memory storage, which works fine for single-session use.

---

## Prerequisites

### Required

- **Python 3.11+**
- **OpenAI API key** — get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys) and put it in `.env`

### Optional (for full functionality)

- **Redis** — session memory. Without it, the system uses in-memory fallback.
  - Windows: [download here](https://github.com/microsoftarchive/redis/releases)
  - Mac/Linux: `brew install redis` or `apt-get install redis-server`

---

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/BalajiV21/AI_Compliance_Auditor.git
cd AI_Compliance_Auditor

python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
# Windows
copy .env.example .env
# Mac/Linux
cp .env.example .env
```

Key settings in `.env`:

```bash
OPENAI_API_KEY=sk-...your-key...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TEMPERATURE=0.1

CHROMA_PERSIST_DIR=./data/chroma_db
EMBEDDING_MODEL=text-embedding-3-small

TOP_K_RESULTS=5
CHUNK_SIZE=512
CHUNK_OVERLAP=50

MAX_ITERATIONS=10
ENABLE_SELF_REFLECTION=true
```

### 3. Add your OpenAI key

Edit `.env` and replace the placeholder with your real key from
[platform.openai.com/api-keys](https://platform.openai.com/api-keys).

### 4. Load documents into the vector store

```bash
python setup.py
```

### 5. Start the API server

```bash
python src/api/main.py
# API:  http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 6. Run the frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
# Uses the mock event stream by default (frontend/.env.development sets VITE_USE_MOCK=true),
# so you can develop the UI without needing the backend running.
```

For a production build served against the real backend:

```bash
npm run build
# Output in frontend/dist/ — serve with any static host + reverse-proxy /api/* to the FastAPI port.
```

---

## Usage

### Web UI

Open the app in your browser, type a compliance question, click **Ask**. The workflow trace on the right ticks through *Retrieving → Generating → Reflecting* as it works. When the answer appears, click a `[1] p.2` chip to jump the PDF to that page and highlight the exact cited passage.

Questions to try:
- *"What is the right to erasure under GDPR Article 17?"*
- *"What are the principles for processing personal data under GDPR Article 5?"*
- *"How does HIPAA define Protected Health Information?"*
- *"What security safeguards does SOC2 require for access controls?"*

### REST API — streaming

```bash
curl -N -X POST "http://localhost:8000/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the right to erasure under GDPR?"}'
```

Emits Server-Sent Events: `start → retrieved → generating → reflecting → answer → done`.

### REST API — synchronous

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the right to erasure under GDPR?", "session_id": "test_session"}'
```

### Python

```python
from retrieval import VectorStore, CitationRetriever
from agents import ComplianceAgent, create_langchain_tools

vector_store = VectorStore(
    persist_directory="./data/chroma_db",
    collection_name="compliance_documents"
)
retriever = CitationRetriever(vector_store)
tools = create_langchain_tools(retriever)

agent = ComplianceAgent(
    retriever=retriever,
    tools=tools,
    model_name="gpt-4o-mini"
)

result = agent.run("What is GDPR Article 17 about?")
print(result['answer'])
```

---

## Evaluation

The system is evaluated with [RAGAS](https://docs.ragas.io/) across four dimensions using `gpt-4o-mini` as the LLM judge. Ten hand-picked compliance questions with reference answers spanning GDPR, HIPAA and SOC 2. Full per-question output lives in [docs/ragas_report.json](docs/ragas_report.json).

| Metric | Score | What it measures |
|---|---|---|
| Faithfulness       | **0.88**  | Are the answer's claims grounded in the retrieved chunks (no hallucination)? |
| Answer Relevancy   | **0.90**  | Does the answer actually address the question asked? |
| Context Precision  | **0.81**  | Are the retrieved chunks relevant to the question? |
| Context Recall     | **0.66**  | Do the retrieved chunks cover the full reference answer? |

*(n = 10 questions, gpt-4o-mini for both generation and judging, text-embedding-3-small for retrieval.)*

### Reading the numbers

- **Faithfulness 0.88 + Answer Relevancy 0.90** — the model reliably answers what's asked and stays grounded in the retrieved text. Very few made-up claims.
- **Context Precision 0.81** — the top-k retrieval mostly returns on-topic chunks, though a small fraction are noise.
- **Context Recall 0.66** — the weakest score, and expected: the sample docs are *excerpts*, so some reference-answer content simply isn't in the corpus for retrieval to find. This is a data-coverage issue, not a retrieval-algorithm issue. Ingesting the full regulations (rather than the sample text files) would lift this substantially.

### Reproducing

```bash
python src/evaluation/ragas_eval.py
```

Runs the agent on the test set, scores every prediction with RAGAS, and writes `docs/ragas_report.json` + `docs/ragas_report.csv`. Total cost per run: about $0.05 in OpenAI API charges.

---

## Challenges & What I Learned

**Getting the self-reflection loop to terminate reliably**
The hardest part was defining what "good enough" means for the reflection step. Without a clear exit condition, the loop either never triggered or ran all 10 iterations on every query. I ended up using RAGAS faithfulness as the quality signal — if the retrieved chunks scored below a threshold against the generated answer, the agent retried; otherwise it stopped. Getting the threshold right took a lot of trial runs. Too strict and it always loops; too loose and it never catches bad answers.

**Hybrid retrieval was harder to tune than I expected**
Combining semantic and BM25 results means you need a reranking step, otherwise you just get two noisy lists merged together. I tried a few approaches before settling on a weighted combination that prioritizes semantic similarity but bumps up results with exact article-number matches. Queries that mix a conceptual question with a specific article reference are still the trickiest case.

**Redis adds real operational complexity**
Early on I had no fallback logic, which meant the system crashed if Redis wasn't running. Adding an in-memory fallback made it actually usable without the full stack. If I were starting over, I'd design optional services from day one instead of retrofitting it.

**Chunking strategy matters more than the model**
I spent a lot of time tuning the LLM and almost no time on chunking — until I realized retrieval quality was the bottleneck, not generation. Switching from fixed-size chunks to semantic chunking (splitting on paragraph and section boundaries) improved context recall noticeably. The lesson was pretty clear: no amount of agent sophistication fixes bad retrieval.

---

## What's Next

- **Chunker + retrieval unit tests** — a recent infinite-loop bug in the chunker (fixed) is exactly the class of issue a small pytest suite would catch pre-deploy
- **Lift context recall (currently 0.66)** — ingest the full regulation texts rather than sample excerpts, so the reference-answer content actually exists in the corpus for retrieval to find
- **True multi-agent** — split the single ComplianceAgent into per-regulation Specialists coordinated by a Planner/Supervisor, so cross-regulation questions get fanned-out in parallel instead of muddled through one prompt
- **HTTPS via Let's Encrypt** — the site currently runs plain HTTP; adding TLS is a 30-minute nginx + certbot step
- **API auth + rate limiting** — right now the streaming endpoint is public, meaning anyone with the URL can spend OpenAI credits on my key
- **Ingest real PDFs, not the .txt samples** — chunks currently default to `page_number=1`, so citations don't always land on the exact page of the rendered PDF viewer
- **Docker Compose** — containerize the whole stack (API + Redis + ChromaDB + nginx) so the whole thing comes up with one command

---

## Project Structure

```
Agentic_Compliance_Auditor/
├── src/
│   ├── agents/              # LangGraph agent and tools
│   │   ├── compliance_agent.py
│   │   └── tools.py
│   ├── memory/              # Redis integration (with in-memory fallback)
│   │   └── redis_memory.py
│   ├── retrieval/           # ChromaDB + hybrid (semantic + BM25) retriever
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── ingestion/           # Document loading and chunking
│   │   ├── document_loader.py
│   │   └── chunker.py
│   ├── evaluation/          # RAGAS evaluation pipeline
│   │   └── ragas_eval.py
│   └── api/                 # FastAPI server (REST + SSE streaming)
│       └── main.py
├── frontend/                # React + Vite + TypeScript UI
│   ├── src/
│   │   ├── components/      # PdfViewer, TracePanel, AnswerBox, RegulationTabs, QuestionInput
│   │   ├── store.ts         # Zustand global state
│   │   ├── mockStream.ts    # Dev-time fake SSE producer
│   │   ├── realStream.ts    # Production SSE client hitting /api/query/stream
│   │   └── types.ts         # Shared event / chunk types
│   ├── public/              # GDPR.pdf / HIPAA.pdf / SOC2.pdf served to the viewer
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   └── build_public_pdfs.py # Converts data/sample_docs/*.txt → frontend/public/*.pdf
├── data/
│   ├── sample_docs/         # Source regulatory text files (GDPR / HIPAA / SOC2)
│   └── chroma_db/           # Persisted vector index
├── config/
│   └── config.py            # Pydantic-settings loader over .env
├── docs/                    # Project write-ups + PDF walkthroughs
├── requirements.txt
├── setup.py                 # Runs ingestion into ChromaDB
└── README.md
```

---

## Troubleshooting

**OpenAI auth error**
```
AuthenticationError: Incorrect API key provided
→ Check OPENAI_API_KEY in .env — must start with `sk-` and have no quotes/spaces.
  Confirm the key is active at https://platform.openai.com/api-keys
```

**OpenAI rate limit / quota**
```
RateLimitError / You exceeded your current quota
→ Check your usage and billing at https://platform.openai.com/account/billing
  gpt-4o-mini is ~$0.15 / 1M input tokens, so normal dev use is cheap.
```

**ChromaDB dimension mismatch**
```
chromadb.errors.InvalidDimensionException
→ Delete data/chroma_db/ and re-run python setup.py
  (usually happens after switching embedding models)
```

**Redis connection refused**
```
Warning: Could not connect to Redis. Using fallback.
→ This is fine — the system continues with in-memory storage.
  Start Redis only if you need cross-session memory to persist.
```

---

## Resources

- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [ChromaDB docs](https://docs.trychroma.com/)
- [OpenAI model reference](https://platform.openai.com/docs/models)
- [RAGAS docs](https://docs.ragas.io/)

---

## License

MIT

---

Built by [Balaji V](https://github.com/BalajiV21)
