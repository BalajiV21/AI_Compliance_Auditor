"""
Ultra-Lightweight Setup Script
No embeddings, no heavy models - just stores text directly in ChromaDB
"""
import sys
import gc
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from loguru import logger
import chromadb
from chromadb.config import Settings

# Configuration
CHROMA_DIR  = "./data/chroma_db"
SAMPLE_DIR  = "./data/sample_docs"
COLLECTION  = "compliance_documents"
CHUNK_SIZE  = 150   # Very small chunks


def infer_doc_type(filename: str) -> str:
    f = filename.lower()
    if   "gdpr"  in f: return "GDPR"
    elif "hipaa" in f: return "HIPAA"
    elif "soc2"  in f: return "SOC2"
    else:              return "General"


def main():
    print("=" * 60)
    print("Agentic Compliance Auditor - Ultra Lite Setup")
    print("=" * 60)

    # Step 1: Setup ChromaDB first
    print("\n Setting up ChromaDB...")
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

    # Step 2: Process one file at a time to save RAM
    print("\n Processing documents one at a time...")
    sample_path = Path(SAMPLE_DIR)
    total_chunks = 0

    for txt_file in sample_path.glob("*.txt"):
        doc_type = infer_doc_type(txt_file.name)
        print(f"\n  Loading: {txt_file.name}")

        # Read file
        text = txt_file.read_text(encoding="utf-8")
        lines = text.split("\n")

        # Build small chunks line by line
        chunks, ids, metas = [], [], []
        current = ""
        chunk_idx = 0

        for line in lines:
            current += line + "\n"
            if len(current) >= CHUNK_SIZE:
                chunk_text = current.strip()
                if chunk_text:
                    safe_name = txt_file.name.replace(".", "_")
                    chunks.append(chunk_text)
                    ids.append(f"{safe_name}_{chunk_idx}")
                    metas.append({
                        "filename": txt_file.name,
                        "document_type": doc_type,
                        "chunk_index": chunk_idx,
                    })
                    chunk_idx += 1
                current = ""

        # Add leftover text
        if current.strip():
            safe_name = txt_file.name.replace(".", "_")
            chunks.append(current.strip())
            ids.append(f"{safe_name}_{chunk_idx}")
            metas.append({
                "filename": txt_file.name,
                "document_type": doc_type,
                "chunk_index": chunk_idx,
            })

        print(f"  Created {len(chunks)} chunks")

        # Insert one chunk at a time to save RAM
        inserted = 0
        for i in range(len(chunks)):
            try:
                collection.add(
                    ids       =[ids[i]],
                    documents =[chunks[i]],
                    metadatas =[metas[i]],
                )
                inserted += 1
            except Exception as e:
                print(f"  Warning: skipped chunk {i}: {e}")

        print(f"  Stored {inserted} chunks")
        total_chunks += inserted

        # Free memory after each file
        del text, lines, chunks, ids, metas
        gc.collect()

    # Step 3: Verify
    print(f"\n Verifying...")
    count = collection.count()
    print(f"  Total chunks in DB: {count}")

    # Step 4: Test search
    print("\n Testing search...")
    results = collection.query(
        query_texts=["data retention"],
        n_results=1
    )

    if results["ids"] and results["ids"][0]:
        print("  Search working!")
    else:
        print("  Warning: search returned no results")

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"  Total chunks stored: {count}")
    print("\nNext steps:")
    print("  1. Start Ollama:  ollama serve")
    print("  2. Start API:     cd src/api && python main.py")
    print("  3. Start UI:      cd ui && streamlit run streamlit_app.py")
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\n Setup failed: {e}")
        logger.exception("Setup error")
        sys.exit(1)