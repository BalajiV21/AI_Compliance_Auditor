#  Agentic Compliance Auditor

An advanced regulatory compliance auditing system that helps organizations automatically analyze documents for compliance requirements using autonomous agents, enhanced memory systems, and intelligent document retrieval.

##  Overview

This system combines **Agentic RAG** (Retrieval Augmented Generation) with **multi-tier memory systems** to provide accurate, cited, and contextually-aware compliance analysis. The platform functions as an intelligent compliance officer that can reason through complex regulatory requirements.
[![Compliance Auditor UI](img/Screenshot 2026-02-18 030721.png)]

### Key Features

-  Agentic RAG: Autonomous agents using LangGraph that can plan, reason, use tools, and self-reflect
-  Hybrid Retrieval: Semantic search + keyword matching + metadata filtering for precision
-  Multi-Tier Memory: Redis for session management, Neo4j for knowledge graphs
-  Citation Tracking: Every answer includes source citations with article/section references
-  Evaluation Framework: RAGAS-based evaluation for quality assurance
-  Production-Ready: FastAPI server + Streamlit UI + comprehensive logging

### Supported Regulations

- **GDPR** (General Data Protection Regulation)
- **HIPAA** (Health Insurance Portability and Accountability Act)
- **SOC2** (Service Organization Control 2)
- Extensible to any regulatory framework

##  Architecture

```
┌─────────────────────────────────────┐
│   Agentic Layer (LangGraph)         │  ← Decision-making, reasoning
├─────────────────────────────────────┤
│   Memory Layer (Multi-tier)         │  ← Context retention
│   • Redis (session cache)           │
│   • Neo4j (entity relationships)    │
├─────────────────────────────────────┤
│   Retrieval Layer (Hybrid RAG)      │  ← Document search
│   • ChromaDB (vector storage)       │
│   • Semantic + Keyword search       │
│   • Citation tracking                │
└─────────────────────────────────────┘
```

##  Prerequisites

### Required Software

1. **Python 3.11+**
2. **Ollama** (for local LLM inference)
   - Install from: https://ollama.ai
   - Pull model: `ollama pull llama3.2`

### Optional Components (for full functionality)

3. **Redis** (for session memory)
   - Windows: https://github.com/microsoftarchive/redis/releases
   - Linux/Mac: `brew install redis` or `apt-get install redis-server`

4. **Neo4j** (for knowledge graph)
   - Download from: https://neo4j.com/download/
   - Or use Docker: `docker run -p 7474:7474 -p 7687:7687 neo4j`

> **Note**: The system will work without Redis and Neo4j using fallback in-memory storage, but with reduced capabilities.

##  Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/BalajiV21/AI_Compliance_Auditor.git
cd AI_Compliance_Auditor

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your settings (optional if using defaults)
```

### 3. Start Ollama (Required)

```bash
# Make sure Ollama is running
ollama serve

# In another terminal, verify the model is available
ollama pull llama3.2
```

### 4. Initialize the Vector Database

```bash
# Run the setup script to load sample documents
python setup.py
```

### 5. Start the API Server

```bash
# From the src/api directory
cd src/api
python main.py

# Server will start at http://localhost:8000
# API docs available at http://localhost:8000/docs
```

### 6. Launch the Streamlit UI

```bash
# In a new terminal, activate venv and run
cd ui
streamlit run streamlit_app.py

# UI will open at http://localhost:8501
```

##  Usage

### Using the Streamlit UI

1. Open http://localhost:8501
2. Enter your compliance question in the text area
3. Click "Submit Query"
4. View the answer with citations and sources

**Sample Questions**:
- "What are the requirements for data retention under GDPR Article 17?"
- "How does HIPAA define Protected Health Information?"
- "What are the security safeguards required by SOC2?"

### Using the API

```bash
# Test with curl
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the right to erasure under GDPR?",
    "session_id": "test_session",
    "use_simple_agent": false
  }'
```

### Using Python

```python
from retrieval import VectorStore, CitationRetriever
from agents import ComplianceAgent, create_langchain_tools

# Initialize components
vector_store = VectorStore(
    persist_directory="./data/chroma_db",
    collection_name="compliance_documents"
)
retriever = CitationRetriever(vector_store)
tools = create_langchain_tools(retriever)

agent = ComplianceAgent(
    retriever=retriever,
    tools=tools,
    model_name="llama3.2"
)

# Ask a question
result = agent.run("What is GDPR Article 17 about?")
print(result['answer'])
```

##  Project Structure

```
AI_Compliance_Auditor/
├── src/
│   ├── agents/              # LangGraph agents and tools
│   │   ├── compliance_agent.py
│   │   └── tools.py
│   ├── memory/              # Memory systems
│   │   ├── redis_memory.py
│   │   └── neo4j_graph.py
│   ├── retrieval/           # Vector DB and retrieval
│   │   ├── vector_store.py
│   │   └── retriever.py
│   ├── ingestion/           # Document processing
│   │   ├── document_loader.py
│   │   └── chunker.py
│   ├── evaluation/          # RAGAS evaluation
│   │   └── ragas_eval.py
│   ├── api/                 # FastAPI server
│   │   └── main.py
│   └── utils/               # Helper functions
├── ui/
│   └── streamlit_app.py    # Streamlit interface
├── data/
│   ├── sample_docs/         # Sample regulatory documents
│   ├── raw/                 # Your documents (PDFs)
│   ├── processed/           # Processed chunks
│   └── chroma_db/           # Vector database
├── config/
│   └── config.py            # Configuration management
├── requirements.txt         # Python dependencies
├── setup.py                 # Database initialization
├── .env.example             # Example environment variables
├── .gitignore
└── README.md
```

##  Configuration

Key settings in `.env` or `config/config.py`:

```bash
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Vector Database
CHROMA_PERSIST_DIR=./data/chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Retrieval
TOP_K_RESULTS=5
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Agent
MAX_ITERATIONS=10
ENABLE_SELF_REFLECTION=true
```

##  Evaluation

Run the evaluation framework to assess system performance:

```bash
cd src/evaluation
python ragas_eval.py
```

This will:
- Run test queries against the system
- Evaluate retrieval quality
- Assess answer accuracy and citations
- Generate a detailed report

##  How It Works

### 1. Document Ingestion

```python
# Documents are loaded, chunked semantically, and embedded
Document → Semantic Chunking → Embeddings → Vector Store
```

### 2. Query Processing

```python
User Query → Agent Plans → Retrieves Docs → LLM Generates → Self-Reflects → Answer
```

### 3. Agentic Workflow (LangGraph)

The agent follows this workflow:
1. **Retrieve**: Get relevant documents from vector store
2. **Generate**: Create answer using LLM with context
3. **Tool Use**: Call tools if needed (search, cross-reference, etc.)
4. **Reflect**: Self-critique the answer for accuracy
5. **Iterate**: Repeat if improvements needed (max 10 iterations)

### 4. Memory Systems

- **Redis**: Stores conversation history for context
- **Neo4j**: Maintains knowledge graph of regulations, articles, and requirements

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test individual components
python src/ingestion/document_loader.py
python src/retrieval/vector_store.py
python src/agents/compliance_agent.py
```

##  Performance Tips

1. **Use GPU acceleration**: If available, Ollama will use GPU automatically
2. **Adjust chunk size**: Smaller chunks (256) for precise answers, larger (1024) for context
3. **Enable reranking**: Set `RERANK_ENABLED=true` for better precision (requires Cohere API)
4. **Simple agent mode**: Use for faster responses when full reasoning isn't needed

##  Security Notes

- All processing is local by default (using Ollama)
- No data sent to external APIs unless you configure external LLM providers
- Redis and Neo4j should be secured in production environments

##  Troubleshooting

### Ollama Connection Error
```
Error: Could not connect to Ollama
Solution: Ensure Ollama is running with `ollama serve`
```

### ChromaDB Error
```
Error: chromadb.errors.InvalidDimensionException
Solution: Delete data/chroma_db and re-run ingestion
```

### Out of Memory
```
Error: CUDA out of memory / RAM exhausted
Solution: Use a smaller model (llama3.2:1b) or reduce chunk size
```

### Redis Connection Refused
```
Warning: Could not connect to Redis. Using fallback.
Solution: Start Redis server or continue with in-memory fallback
```

##  Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [Ollama Models](https://ollama.ai/library)
- [RAGAS Evaluation](https://docs.ragas.io/)

##  Contributing

To extend this system:

1. **Add new regulations**: Place PDFs in `data/raw/` and run ingestion
2. **Create custom tools**: Add to `src/agents/tools.py`
3. **Modify agent behavior**: Edit `src/agents/compliance_agent.py`
4. **Add evaluation metrics**: Extend `src/evaluation/ragas_eval.py`

##  License

This project is for educational and demonstration purposes.

##  Acknowledgments

Built with:
- **LangChain** & **LangGraph** - Agent framework
- **ChromaDB** - Vector database
- **Ollama** - Local LLM inference
- **FastAPI** - API framework
- **Streamlit** - UI framework
- **Sentence Transformers** - Embeddings

---

**Developed for compliance professionals and regulatory analysis**

For questions or issues, please check the logs in `logs/app.log` or review the project documentation.
