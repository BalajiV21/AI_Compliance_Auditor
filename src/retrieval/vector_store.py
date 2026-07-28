"""
Vector store implementation using ChromaDB with direct OpenAI embeddings.

We call the OpenAI SDK ourselves and pass computed vectors to ChromaDB.
This bypasses chromadb's built-in embedding-function wrapper (which
silently hangs on some version combos) and gives real error messages
when things go wrong.

Memory footprint is negligible — no local ML model is loaded.
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from loguru import logger
from pathlib import Path
import json

from openai import OpenAI

try:
    from config import settings as _settings
except Exception:
    _settings = None


EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dim
OPENAI_TIMEOUT = 30


def _resolve_openai_key() -> str:
    key = (getattr(_settings, "OPENAI_API_KEY", None) if _settings else None) \
          or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OPENAI_API_KEY not set. Add it to .env or export it before using VectorStore."
        )
    return key


class VectorStore:
    """
    ChromaDB-based vector store for semantic search.
    Embeddings computed via OpenAI (text-embedding-3-small) with an explicit timeout.
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "compliance_documents",
        embedding_model: str = EMBEDDING_MODEL,
    ):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        self.openai_client = OpenAI(api_key=_resolve_openai_key(), timeout=OPENAI_TIMEOUT)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # Collection has no embedding_function — we always pass embeddings explicitly.
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "Compliance and regulatory documents",
                "hnsw:space": "cosine",
            },
        )

        logger.info(
            f"VectorStore ready: collection={collection_name}, "
            f"embedding_model={embedding_model}"
        )

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Call OpenAI embeddings API for a batch of texts."""
        resp = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [d.embedding for d in resp.data]

    def add_documents(self, chunks: List, batch_size: int = 100):
        """Add document chunks, embedding each batch via OpenAI."""
        logger.info(f"Adding {len(chunks)} chunks to vector store")

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            ids = [chunk.chunk_id for chunk in batch]
            documents = [chunk.content for chunk in batch]
            metadatas = [self._prepare_metadata(chunk.metadata) for chunk in batch]

            embeddings = self._embed(documents)
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info(f"Added batch {i // batch_size + 1} ({len(batch)} chunks)")

        logger.info("All chunks added successfully")

    def _prepare_metadata(self, metadata: Dict) -> Dict:
        """Coerce metadata into Chroma-compatible primitives."""
        clean_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, list):
                clean_metadata[key] = json.dumps(value)
            elif value is None:
                clean_metadata[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            else:
                clean_metadata[key] = str(value)
        return clean_metadata

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Dict]:
        """Semantic search: embed the query via OpenAI, then query ChromaDB."""
        logger.info(f"Searching for: '{query}' (top_k={top_k})")

        where = None
        if filter_metadata:
            where = self._build_where_clause(filter_metadata)

        query_embedding = self._embed([query])[0]

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        formatted_results = []
        for i in range(len(results['ids'][0])):
            distance = results['distances'][0][i]
            raw_similarity = max(0.0, 1 - distance)
            formatted_results.append({
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': self._restore_metadata(results['metadatas'][0][i]),
                'distance': distance,
                'similarity_score': raw_similarity,
            })

        logger.info(f"Found {len(formatted_results)} results")
        return formatted_results

    def _build_where_clause(self, filter_metadata: Dict) -> Dict:
        """Build ChromaDB where clause from filter metadata"""
        where_conditions = {}
        for key, value in filter_metadata.items():
            if isinstance(value, list):
                where_conditions[key] = {"$in": value}
            else:
                where_conditions[key] = {"$eq": value}
        return where_conditions

    def _restore_metadata(self, metadata: Dict) -> Dict:
        """Restore metadata from ChromaDB format"""
        restored = {}
        for key, value in metadata.items():
            if isinstance(value, str) and value.startswith('['):
                try:
                    restored[key] = json.loads(value)
                except Exception:
                    restored[key] = value
            else:
                restored[key] = value
        return restored


class MultiCollectionVectorStore:
    """Manage multiple named VectorStore collections behind one persist directory."""

    def __init__(self, persist_directory: str, embedding_model: str = EMBEDDING_MODEL):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self.collections: Dict[str, VectorStore] = {}

    def get_collection(self, collection_name: str) -> VectorStore:
        if collection_name not in self.collections:
            self.collections[collection_name] = VectorStore(
                persist_directory=self.persist_directory,
                collection_name=collection_name,
                embedding_model=self.embedding_model,
            )
        return self.collections[collection_name]

    def search_all_collections(
        self,
        query: str,
        top_k_per_collection: int = 3,
    ) -> Dict[str, List[Dict]]:
        return {
            name: coll.search(query, top_k=top_k_per_collection)
            for name, coll in self.collections.items()
        }
