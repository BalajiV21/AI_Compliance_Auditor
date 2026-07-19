"""
Ingestion setup for the Agentic Compliance Auditor.

Uses the real DocumentLoader + RegulationChunker so metadata (including
page_number for PDFs) flows into ChromaDB. Wipes the collection first
so a re-run always produces a clean, consistent index.
"""
import sys
import gc
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from loguru import logger
import chromadb
from chromadb.config import Settings
import json

from ingestion.document_loader import DocumentLoader
from ingestion.chunker import RegulationChunker

CHROMA_DIR    = "./data/chroma_db"
SAMPLE_DIR    = "./data/sample_docs"
COLLECTION    = "compliance_documents"
CHUNK_SIZE    = 512
CHUNK_OVERLAP = 50


def _clean_metadata(md: dict) -> dict:
    """Coerce chunk metadata into Chroma-compatible primitives."""
    out = {}
    for k, v in md.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, (list, dict)):
            out[k] = json.dumps(v)
        else:
            out[k] = str(v)
    return out


def main():
    print("=" * 60)
    print("Agentic Compliance Auditor - Ingestion")
    print("=" * 60)

    print("\n Resetting ChromaDB...")
    Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    print("  ChromaDB ready")

    loader = DocumentLoader()
    chunker = RegulationChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    sample_path = Path(SAMPLE_DIR)
    if not sample_path.exists():
        print(f"  Sample dir missing: {sample_path}")
        return False

    total_chunks = 0

    for file_path in sorted(sample_path.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() not in loader.supported_formats:
            continue

        print(f"\n  Loading: {file_path.name}")
        try:
            document = loader.load_document(str(file_path))
        except Exception as e:
            print(f"  Skipped ({e})")
            continue

        chunks = chunker.chunk_document(document)
        print(f"  Created {len(chunks)} chunks")

        inserted = 0
        for chunk in chunks:
            try:
                collection.add(
                    ids=[chunk.chunk_id],
                    documents=[chunk.content],
                    metadatas=[_clean_metadata(chunk.metadata)],
                )
                inserted += 1
            except Exception as e:
                print(f"  Warning: skipped chunk {chunk.chunk_id}: {e}")

        print(f"  Stored {inserted} chunks")
        total_chunks += inserted

        del document, chunks
        gc.collect()

    print("\n Verifying...")
    count = collection.count()
    print(f"  Total chunks in DB: {count}")

    print("\n Testing search...")
    results = collection.query(query_texts=["data retention"], n_results=1)
    if results["ids"] and results["ids"][0]:
        md = results["metadatas"][0][0]
        print(f"  Top hit: {md.get('filename')}  page={md.get('page_number')}")
    else:
        print("  Warning: search returned no results")

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"  Total chunks stored: {count}")
    print("\nNext steps:")
    print("  1. Confirm OPENAI_API_KEY is set in .env")
    print("  2. Start API:     python src/api/main.py")
    print("  3. Curl stream:   curl -N -X POST http://localhost:8000/query/stream \\")
    print("                        -H 'Content-Type: application/json' \\")
    print("                        -d '{\"query\":\"GDPR Article 17?\"}'")
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\n Setup failed: {e}")
        logger.exception("Setup error")
        sys.exit(1)
