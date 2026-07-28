"""
Ingestion setup for the Agentic Compliance Auditor.

Computes embeddings by calling OpenAI directly (no chromadb wrapper),
so failures produce real error messages instead of silent hangs.

Prints progress after every step and flushes stdout so live tail
`tail -f /tmp/ingest.log` shows work in real time.
"""
import os
import sys
import gc
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger
import chromadb
from chromadb.config import Settings
from openai import OpenAI

from ingestion.document_loader import DocumentLoader
from ingestion.chunker import RegulationChunker

CHROMA_DIR      = "./data/chroma_db"
SAMPLE_DIR      = "./data/sample_docs"
COLLECTION      = "compliance_documents"
CHUNK_SIZE      = 512
CHUNK_OVERLAP   = 50
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dim, ~$0.02 per 1M tokens
BATCH           = 100


def log(msg: str) -> None:
    """Print with an immediate flush so tail -f shows it right away."""
    print(msg, flush=True)


def _clean_metadata(md: dict) -> dict:
    import json
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


def main() -> bool:
    log("=" * 60)
    log("Agentic Compliance Auditor - Ingestion")
    log("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log("  ERROR: OPENAI_API_KEY not set (.env or environment).")
        return False

    openai_client = OpenAI(api_key=api_key, timeout=30)

    log("\n Resetting ChromaDB...")
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
    log(f"  ChromaDB ready (embeddings via OpenAI {EMBEDDING_MODEL})")

    loader = DocumentLoader()
    chunker = RegulationChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    sample_path = Path(SAMPLE_DIR)
    if not sample_path.exists():
        log(f"  Sample dir missing: {sample_path}")
        return False

    total_chunks = 0

    for file_path in sorted(sample_path.iterdir()):
        if not file_path.is_file() or file_path.suffix.lower() not in loader.supported_formats:
            continue

        log(f"\n  Loading: {file_path.name}")
        try:
            document = loader.load_document(str(file_path))
        except Exception as e:
            log(f"  Skipped ({e})")
            continue

        chunks = chunker.chunk_document(document)
        log(f"  Created {len(chunks)} chunks")

        inserted = 0
        for start in range(0, len(chunks), BATCH):
            batch = chunks[start:start + BATCH]
            docs = [c.content for c in batch]

            log(f"    embedding batch {start // BATCH + 1} ({len(docs)} chunks) via OpenAI...")
            try:
                resp = openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=docs,
                )
                vectors = [d.embedding for d in resp.data]
            except Exception as e:
                log(f"    OpenAI embedding failed: {e}")
                continue

            log(f"    writing {len(vectors)} vectors to ChromaDB...")
            collection.add(
                ids=[c.chunk_id for c in batch],
                documents=docs,
                embeddings=vectors,
                metadatas=[_clean_metadata(c.metadata) for c in batch],
            )
            inserted += len(batch)
            log(f"    stored batch {start // BATCH + 1}")

        log(f"  Total for {file_path.name}: {inserted} chunks")
        total_chunks += inserted

        del document, chunks
        gc.collect()

    log("\n Verifying...")
    count = collection.count()
    log(f"  Total chunks in DB: {count}")

    log("\n Testing search...")
    try:
        q_resp = openai_client.embeddings.create(
            model=EMBEDDING_MODEL, input=["data retention"],
        )
        q_vec = q_resp.data[0].embedding
        results = collection.query(query_embeddings=[q_vec], n_results=1)
        if results["ids"] and results["ids"][0]:
            md = results["metadatas"][0][0]
            log(f"  Top hit: {md.get('filename')}  page={md.get('page_number')}")
        else:
            log("  Warning: search returned no results")
    except Exception as e:
        log(f"  Search test failed: {e}")

    log("\n" + "=" * 60)
    log("Setup Complete!")
    log("=" * 60)
    log(f"  Total chunks stored: {count}")
    log("\nNext steps:")
    log("  1. sudo systemctl restart compliance-api")
    log("  2. curl -N -X POST http://localhost:8000/query/stream \\")
    log("         -H 'Content-Type: application/json' \\")
    log("         -d '{\"query\":\"GDPR Article 17?\"}'")
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except KeyboardInterrupt:
        log("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        log(f"\n Setup failed: {e}")
        logger.exception("Setup error")
        sys.exit(1)
