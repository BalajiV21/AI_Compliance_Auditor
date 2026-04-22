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

## Screenshots

### Main Interface
![Main UI](img/Screenshot%202026-02-18%20030721.png)

### Query with Cited Answer
![Query Result](img/Screenshot%202026-02-18%20031943.png)
*The agent returns an answer grounded in retrieved chunks, with source document and article reference shown below.*

### Citation Breakdown
![Answer Detail](img/Screenshot%202026-02-18%20032039.png)
*Each answer links back to the specific article and section it pulled from — no black-box responses.*

### Conversation History
![Conversation History](img/Screenshot%202026-02-18%20032248.png)

### Settings & System Stats
![Settings Sidebar](img/Screenshot%202026-02-18%20032306.png)

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Agent Framework | LangGraph | State machine for multi-step reasoning and self-reflection loops |
| LLM | OpenAI (gpt-4o-mini) | Fast, cheap, strong reasoning — ~$0.15 per 1M input tokens |
| Vector DB | ChromaDB | Semantic document search and storage |
| Session Memory | Redis | Conversation context across queries |
| Knowledge Graph | Neo4j | Entity relationships between regulations and requirements |
| API | FastAPI | REST endpoints for the agent |
| UI | Streamlit | Frontend for running compliance queries |
| Evaluation | RAGAS | Measuring faithfulness, recall, and citation accuracy |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) | Document and query embeddings |

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
    │    (query embedded in-process via sentence-transformers, │
    │     all-MiniLM-L6-v2, 384-dim)                           │
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
    ├──►  Redis   (session history keyed by session_id; in-memory fallback if Redis is down)
    └──►  Neo4j   (regulation → article → requirement relationships; optional, skipped if offline)
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

**Why Neo4j for the knowledge graph?**
Compliance data has natural graph structure: Articles contain Requirements, Requirements apply to Entities, Entities overlap across regulations. Querying these relationships in a relational DB would mean multi-level joins. In Neo4j it's a two-hop traversal. For cross-regulation queries ("what do both GDPR and HIPAA say about breach notification?"), this makes a real difference.

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

- **Neo4j** — knowledge graph. Without it, cross-regulation reasoning is disabled.
  - Docker: `docker run -p 7474:7474 -p 7687:7687 neo4j`
  - Or [download directly](https://neo4j.com/download/)

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
EMBEDDING_MODEL=all-MiniLM-L6-v2

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

### 6. Launch the UI

```bash
streamlit run ui/streamlit_app.py
# Opens at http://localhost:8501
```

---

## Usage

### Streamlit UI

Open `http://localhost:8501`, type your question, click Submit.

Questions to try:
- *"What are the requirements for data retention under GDPR Article 17?"*
- *"How does HIPAA define Protected Health Information?"*
- *"What security safeguards does SOC2 require for access controls?"*

### REST API

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the right to erasure under GDPR?",
    "session_id": "test_session",
    "use_simple_agent": false
  }'
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

The system includes a RAGAS-based evaluation pipeline that measures retrieval and generation quality. Run it against your loaded documents:

```bash
cd src/evaluation
python ragas_eval.py
```

This runs a set of test queries and scores the system across four dimensions:

| Metric | Score | What it measures |
|---|---|---|
| Faithfulness | — | Are answers grounded in retrieved docs, not hallucinated? |
| Answer Relevancy | — | Does the answer actually address the question asked? |
| Context Recall | — | Are the right chunks being retrieved? |
| Citation Accuracy | — | Are article/section references correct? |

*Run `ragas_eval.py` to generate scores and fill in this table.*

---

## Challenges & What I Learned

**Getting the self-reflection loop to terminate reliably**
The hardest part was defining what "good enough" means for the reflection step. Without a clear exit condition, the loop either never triggered or ran all 10 iterations on every query. I ended up using RAGAS faithfulness as the quality signal — if the retrieved chunks scored below a threshold against the generated answer, the agent retried; otherwise it stopped. Getting the threshold right took a lot of trial runs. Too strict and it always loops; too loose and it never catches bad answers.

**Hybrid retrieval was harder to tune than I expected**
Combining semantic and BM25 results means you need a reranking step, otherwise you just get two noisy lists merged together. I tried a few approaches before settling on a weighted combination that prioritizes semantic similarity but bumps up results with exact article-number matches. Queries that mix a conceptual question with a specific article reference are still the trickiest case.

**Redis and Neo4j add real operational complexity**
Early on I had no fallback logic, which meant the system crashed if either service wasn't running. Adding graceful degradation — in-memory fallback for Redis, disabling graph features if Neo4j is unavailable — made it actually usable without the full stack. If I were starting over, I'd design optional services from day one instead of retrofitting it.

**Chunking strategy matters more than the model**
I spent a lot of time tuning the LLM and almost no time on chunking — until I realized retrieval quality was the bottleneck, not generation. Switching from fixed-size chunks to semantic chunking (splitting on paragraph and section boundaries) improved context recall noticeably. The lesson was pretty clear: no amount of agent sophistication fixes bad retrieval.

---

## What's Next

- **Streaming responses** — the current setup blocks until the full answer is ready; streaming would make long agent chains feel much more responsive
- **Docker Compose setup** — containerizing the whole stack (API + Redis + Neo4j + ChromaDB) would make it one command to run
- **User document upload** — right now you drop PDFs into `data/raw/` and run ingestion manually; a drag-and-drop upload in the UI would make this usable by non-technical teams
- **API authentication** — no auth currently, which is fine locally but a blocker for any real deployment

---

## Project Structure

```
AI_Compliance_Auditor/
├── src/
│   ├── agents/              # LangGraph agent and tools
│   │   ├── compliance_agent.py
│   │   └── tools.py
│   ├── memory/              # Redis and Neo4j integrations
│   │   ├── redis_memory.py
│   │   └── neo4j_graph.py
│   ├── retrieval/           # ChromaDB and hybrid retrieval
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── ingestion/           # Document loading and chunking
│   │   ├── document_loader.py
│   │   └── chunker.py
│   ├── evaluation/          # RAGAS evaluation pipeline
│   │   └── ragas_eval.py
│   ├── api/                 # FastAPI server
│   │   └── main.py
│   └── utils/
├── ui/
│   └── streamlit_app.py
├── data/
│   ├── sample_docs/         # Sample regulatory PDFs
│   ├── raw/                 # Drop your documents here
│   ├── processed/
│   └── chroma_db/
├── config/
│   └── config.py
├── requirements.txt
├── setup.py
├── .env.example
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
