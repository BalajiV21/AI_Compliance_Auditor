"""
Vector store implementation using ChromaDB with OpenAI embeddings.

Uses OpenAI's text-embedding-3-small so the API/setup do not need to load
sentence-transformers locally — that keeps RAM footprint tiny (a few MB
instead of ~500 MB) and makes ingestion feasible on modest hardware like
a t3.medium EC2.
"""
import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from loguru import logger
from pathlib import Path
import json

try:
    from config import settings as _settings
except Exception:
    _settings = None


EMBEDDING_MODEL = "text-embedding-3-small"


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

    Embeddings are computed by OpenAI (text-embedding-3-small) — no local
    ML model is loaded, so this class is safe to instantiate on tiny hosts.
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

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

        # OpenAI embedding function — Chroma calls it automatically on add/query.
        logger.info(f"Using OpenAI embedding model: {embedding_model}")
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=_resolve_openai_key(),
            model_name=embedding_model,
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={
                "description": "Compliance and regulatory documents",
                "hnsw:space": "cosine",
            },
        )

        logger.info(f"Vector store initialized with collection: {collection_name}")

    def add_documents(self, chunks: List, batch_size: int = 100):
        """Add document chunks. Embeddings are produced by OpenAI via the collection's embedding_function."""
        logger.info(f"Adding {len(chunks)} chunks to vector store")

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            ids = [chunk.chunk_id for chunk in batch]
            documents = [chunk.content for chunk in batch]
            metadatas = [self._prepare_metadata(chunk.metadata) for chunk in batch]

            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"Added batch {i // batch_size + 1} ({len(batch)} chunks)")

        logger.info("All chunks added successfully")

    def _prepare_metadata(self, metadata: Dict) -> Dict:
        """
        Prepare metadata for ChromaDB (must be JSON serializable)
        """
        clean_metadata = {}

        for key, value in metadata.items():
            # Convert lists to JSON strings
            if isinstance(value, list):
                clean_metadata[key] = json.dumps(value)
            # Convert None to empty string
            elif value is None:
                clean_metadata[key] = ""
            # Keep primitives as is
            elif isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            # Convert other types to strings
            else:
                clean_metadata[key] = str(value)

        return clean_metadata

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for relevant chunks using semantic similarity

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results with documents and metadata
        """
        logger.info(f"Searching for: '{query}' (top_k={top_k})")

        # Build where clause if filter provided
        where = None
        if filter_metadata:
            where = self._build_where_clause(filter_metadata)

        # Chroma calls our OpenAI embedding function for query_texts automatically.
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            distance = results['distances'][0][i]
            raw_similarity = max(0.0, 1 - distance)
            result = {
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': self._restore_metadata(results['metadatas'][0][i]),
                'distance': distance,
                'similarity_score': raw_similarity,
            }
            formatted_results.append(result)

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
            # Try to parse JSON strings back to lists
            if isinstance(value, str) and value.startswith('['):
                try:
                    restored[key] = json.loads(value)
                except:
                    restored[key] = value
            else:
                restored[key] = value

        return restored

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Hybrid search combining semantic and keyword search

        Args:
            query: Search query
            top_k: Number of results to return
            keywords: Optional keywords to filter by

        Returns:
            Combined search results
        """
        logger.info(f"Performing hybrid search: '{query}'")

        # Semantic search
        semantic_results = self.search(query, top_k=top_k * 2)

        # If keywords provided, filter and re-rank
        if keywords:
            keyword_boosted = []

            for result in semantic_results:
                content_lower = result['content'].lower()
                keyword_matches = sum(
                    1 for kw in keywords if kw.lower() in content_lower
                )

                # Light keyword boost that won't overwhelm semantic ranking
                boost = 1.0 + (keyword_matches * 0.03)
                result['similarity_score'] = min(1.0, result['similarity_score'] * boost)
                result['keyword_matches'] = keyword_matches

                keyword_boosted.append(result)

            # Re-sort by boosted scores
            keyword_boosted.sort(key=lambda x: x['similarity_score'], reverse=True)
            return keyword_boosted[:top_k]

        return semantic_results[:top_k]

    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        count = self.collection.count()

        return {
            'collection_name': self.collection_name,
            'total_chunks': count,
            'embedding_model': self.embedding_model.get_sentence_embedding_dimension(),
            'persist_directory': str(self.persist_directory)
        }

    def delete_collection(self):
        """Delete the entire collection"""
        logger.warning(f"Deleting collection: {self.collection_name}")
        self.client.delete_collection(name=self.collection_name)

    def reset_collection(self):
        """Reset the collection (delete and recreate)"""
        logger.warning(f"Resetting collection: {self.collection_name}")
        try:
            self.client.delete_collection(name=self.collection_name)
        except:
            pass

        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "description": "Compliance and regulatory documents",
                "hnsw:space": "cosine",
            },
        )


class MultiCollectionVectorStore:
    """
    Manage multiple collections for different document types
    """

    def __init__(
        self,
        persist_directory: str,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self.collections = {}

    def get_collection(self, collection_name: str) -> VectorStore:
        """Get or create a collection"""
        if collection_name not in self.collections:
            self.collections[collection_name] = VectorStore(
                persist_directory=self.persist_directory,
                collection_name=collection_name,
                embedding_model=self.embedding_model
            )

        return self.collections[collection_name]

    def search_all_collections(
        self,
        query: str,
        top_k_per_collection: int = 3
    ) -> Dict[str, List[Dict]]:
        """Search across all collections"""
        results = {}

        for collection_name, collection in self.collections.items():
            results[collection_name] = collection.search(
                query,
                top_k=top_k_per_collection
            )

        return results


if __name__ == "__main__":
    # Test the vector store
    from pathlib import Path
    import sys

    # Add parent directory to path
    sys.path.append(str(Path(__file__).parent.parent))

    from ingestion import DocumentLoader, RegulationChunker

    # Initialize components
    loader = DocumentLoader()
    chunker = RegulationChunker(chunk_size=512, chunk_overlap=50)
    vector_store = VectorStore(
        persist_directory="./data/chroma_db",
        collection_name="test_compliance"
    )

    # Load and process documents
    sample_dir = Path(__file__).parent.parent.parent / "data" / "sample_docs"

    if sample_dir.exists():
        print("Loading documents...")
        docs = loader.load_directory(str(sample_dir))

        print("Chunking documents...")
        all_chunks = []
        for doc in docs:
            chunks = chunker.chunk_document(doc)
            all_chunks.extend(chunks)

        print(f"Adding {len(all_chunks)} chunks to vector store...")
        vector_store.add_documents(all_chunks)

        print("\nCollection stats:")
        print(vector_store.get_collection_stats())

        print("\n\nTesting search:")
        results = vector_store.search("data retention requirements", top_k=3)

        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Document: {result['metadata'].get('filename', 'unknown')}")
            print(f"Similarity: {result['similarity_score']:.4f}")
            print(f"Content: {result['content'][:200]}...")
