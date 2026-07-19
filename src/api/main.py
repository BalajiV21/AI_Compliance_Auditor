"""
FastAPI server for Agentic Compliance Auditor
Provides REST API endpoints for compliance queries
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from loguru import logger
import uuid
import json
from datetime import datetime
from sse_starlette.sse import EventSourceResponse

# Import project components#
#import sys#
#from pathlib import Path#
#sys.path.append(str(Path(__file__).parent.parent))#

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import settings
from retrieval import VectorStore, CitationRetriever
from agents import ComplianceAgent, create_langchain_tools
from memory import RedisMemory, ConversationBufferMemory

# Initialize FastAPI app
app = FastAPI(
    title="Agentic Compliance Auditor API",
    description="AI-powered compliance auditing with autonomous agents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (initialized on startup)
vector_store = None
retriever = None
agent = None
memory = None


# Request/Response models
class QueryRequest(BaseModel):
    query: str = Field(..., description="Compliance question")
    session_id: Optional[str] = Field(None, description="Session ID for conversation context")
    document_type: Optional[str] = Field(None, description="Filter by document type (GDPR, HIPAA, SOC2)")


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict]
    session_id: str
    iterations: Optional[int] = None
    reflection: Optional[str] = None
    timestamp: str


class DocumentUploadResponse(BaseModel):
    message: str
    chunks_added: int
    document_id: str


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, str]
    timestamp: str


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global vector_store, retriever, agent, memory

    logger.info("Starting Agentic Compliance Auditor API...")

    # Initialize vector store
    vector_store = VectorStore(
        persist_directory=settings.CHROMA_PERSIST_DIR,
        collection_name="compliance_documents",
        embedding_model=settings.EMBEDDING_MODEL
    )

    # Initialize retriever
    retriever = CitationRetriever(
        vector_store=vector_store,
        top_k=settings.TOP_K_RESULTS
    )

    # Initialize tools and agent
    tools = create_langchain_tools(retriever)

    agent = ComplianceAgent(
        retriever=retriever,
        tools=tools,
        model_name=settings.OPENAI_MODEL,
        max_iterations=settings.MAX_ITERATIONS,
        enable_reflection=settings.ENABLE_SELF_REFLECTION
    )

    # Initialize memory
    try:
        memory = RedisMemory(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )
    except:
        logger.warning("Using in-memory buffer instead of Redis")
        memory = ConversationBufferMemory()

    logger.info("API startup complete")


@app.get("/", response_model=Dict)
async def root():
    """Root endpoint"""
    return {
        "message": "Agentic Compliance Auditor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components = {
        "api": "healthy",
        "vector_store": "healthy" if vector_store else "unavailable",
        "retriever": "healthy" if retriever else "unavailable",
        "agent": "healthy" if agent else "unavailable",
        "memory": "healthy" if memory else "unavailable"
    }

    # Check vector store
    try:
        stats = vector_store.get_collection_stats()
        if stats['total_chunks'] == 0:
            components["vector_store"] = "empty - no documents loaded"
    except:
        components["vector_store"] = "error"

    overall_status = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        components=components,
        timestamp=datetime.now().isoformat()
    )


@app.post("/query", response_model=QueryResponse)
async def query_compliance(request: QueryRequest):
    """
    Query the compliance auditor

    Args:
        request: Query request with question and optional parameters

    Returns:
        Answer with citations and sources
    """
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"Processing query: '{request.query}' (session: {session_id})")

    try:
        # Store user message in memory
        if isinstance(memory, RedisMemory):
            memory.store_message(session_id, "user", request.query)
        else:
            memory.add_message(session_id, "user", request.query)

        # Run the agentic RAG pipeline
        result = agent.run(request.query)
        result['session_id'] = session_id
        result['timestamp'] = datetime.now().isoformat()

        # Store assistant response in memory
        if isinstance(memory, RedisMemory):
            memory.store_message(session_id, "assistant", result['answer'])
        else:
            memory.add_message(session_id, "assistant", result['answer'])

        logger.info(f"Query completed successfully")

        return QueryResponse(**result)

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_chunk(doc: Dict) -> Dict:
    """Trim a retrieved chunk to what the frontend needs to render + highlight."""
    md = doc.get('metadata', {}) or {}
    return {
        'content': doc.get('content', ''),
        'citation': doc.get('citation', ''),
        'similarity_score': doc.get('similarity_score', 0.0),
        'filename': md.get('filename', ''),
        'document_type': md.get('document_type', ''),
        'page_number': md.get('page_number', 1),
        'section': md.get('section', ''),
    }


def _store_message(session_id: str, role: str, content: str) -> None:
    """Persist a message using whichever memory backend is active."""
    if memory is None:
        return
    if isinstance(memory, RedisMemory):
        memory.store_message(session_id, role, content)
    else:
        memory.add_message(session_id, role, content)


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Stream agent execution as Server-Sent Events.

    Emits phase-completion events so the frontend can render a live workflow trace:
      start       → session_id
      retrieved   → chunks (with page_number for PDF highlighting)
      generating  → LLM call has completed a pass
      reflecting  → reflection text + iteration count (may fire 0..N times)
      answer      → final answer + sources
      done        → stream close
    """
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"Streaming query: '{request.query}' (session: {session_id})")

    _store_message(session_id, "user", request.query)

    async def event_generator():
        final_answer = ""
        final_sources: List[Dict] = []
        iterations = 0
        reflection = ""

        try:
            yield {
                "event": "start",
                "data": json.dumps({"session_id": session_id, "query": request.query}),
            }

            for step in agent.stream(request.query):
                for node_name, state in step.items():
                    if node_name == "retrieve":
                        docs = state.get("retrieved_docs", []) or []
                        final_sources = docs
                        yield {
                            "event": "retrieved",
                            "data": json.dumps({
                                "count": len(docs),
                                "chunks": [_serialize_chunk(d) for d in docs],
                            }),
                        }
                    elif node_name == "generate":
                        if state.get("answer"):
                            final_answer = state["answer"]
                        yield {
                            "event": "generating",
                            "data": json.dumps({"has_answer": bool(final_answer)}),
                        }
                    elif node_name == "reflect":
                        reflection = state.get("reflection", "") or ""
                        iterations = state.get("iterations", 0) or 0
                        yield {
                            "event": "reflecting",
                            "data": json.dumps({
                                "iteration": iterations,
                                "reflection": reflection,
                                "needs_retry": bool(state.get("needs_reflection", False)),
                            }),
                        }

            yield {
                "event": "answer",
                "data": json.dumps({
                    "text": final_answer,
                    "sources": [_serialize_chunk(d) for d in final_sources],
                    "iterations": iterations,
                    "reflection": reflection,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                }),
            }

            _store_message(session_id, "assistant", final_answer)

            yield {"event": "done", "data": json.dumps({})}

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())


@app.get("/search", response_model=List[Dict])
async def search_documents(
    query: str,
    top_k: int = 5,
    document_type: Optional[str] = None
):
    """
    Search for relevant document chunks

    Args:
        query: Search query
        top_k: Number of results
        document_type: Optional filter by document type

    Returns:
        List of matching document chunks with scores
    """
    filter_metadata = {'document_type': document_type} if document_type else None

    results = retriever.retrieve(
        query=query,
        top_k=top_k,
        filter_metadata=filter_metadata
    )

    return results


@app.get("/conversation/{session_id}", response_model=List[Dict])
async def get_conversation_history(session_id: str, limit: Optional[int] = None):
    """
    Get conversation history for a session

    Args:
        session_id: Session identifier
        limit: Optional limit on number of messages

    Returns:
        List of messages
    """
    if isinstance(memory, RedisMemory):
        history = memory.get_conversation_history(session_id, limit=limit)
    else:
        history = memory.get_messages(session_id)
        if limit:
            history = history[-limit:]

    return history


@app.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history for a session"""
    if isinstance(memory, RedisMemory):
        memory.clear_session(session_id)
    else:
        memory.clear(session_id)

    return {"message": f"Conversation {session_id} cleared"}


@app.get("/stats", response_model=Dict)
async def get_statistics():
    """Get system statistics"""
    stats = vector_store.get_collection_stats()

    # Add memory stats if available
    if isinstance(memory, RedisMemory):
        stats['active_sessions'] = len(memory.get_active_sessions())

    return stats


@app.get("/regulations", response_model=List[str])
async def list_regulations():
    """List available regulations"""
    # This would query the vector store for unique document types
    return ["GDPR", "HIPAA", "SOC2"]


@app.post("/ingest")
async def ingest_document(
    background_tasks: BackgroundTasks,
    file_path: str
):
    """
    Ingest a new document (background task)

    Args:
        file_path: Path to document file

    Returns:
        Status message
    """
    document_id = str(uuid.uuid4())

    def process_document():
        from ingestion import DocumentLoader, RegulationChunker

        loader = DocumentLoader()
        chunker = RegulationChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        doc = loader.load_document(file_path)
        chunks = chunker.chunk_document(doc)
        vector_store.add_documents(chunks)

        logger.info(f"Document {document_id} ingested successfully")

    background_tasks.add_task(process_document)

    return {
        "message": "Document ingestion started",
        "document_id": document_id,
        "status": "processing"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
