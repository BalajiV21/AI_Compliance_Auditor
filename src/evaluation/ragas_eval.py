"""
RAGAS evaluation for the Agentic Compliance Auditor.

Runs the compliance agent on a hand-picked set of questions, then scores
the responses with RAGAS across four dimensions:

    - faithfulness       :  is every claim in the answer grounded in retrieved chunks?
    - answer_relevancy   :  does the answer actually address the question asked?
    - context_precision  :  are the retrieved chunks relevant to the question?
    - context_recall     :  do the retrieved chunks cover the reference answer?

Outputs
-------
    docs/ragas_report.json   full per-question + aggregate scores
    docs/ragas_report.csv    per-question metric table (if pandas available)
    stdout                   summary table + a Markdown snippet to paste into README

Cost
----
    ~10 gpt-4o-mini calls for agent inference + ~50-80 gpt-4o-mini calls for RAGAS
    scoring across 4 metrics. Roughly $0.05 for a full run.

Usage
-----
    From the project root (so .env is discovered):

        python src/evaluation/ragas_eval.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- Make imports work regardless of the caller's cwd -----------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env before importing anything that reads OPENAI_API_KEY.
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from loguru import logger
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from retrieval import VectorStore, CitationRetriever
from agents import ComplianceAgent, create_langchain_tools


# ---------------------------------------------------------------------------
# Test set — questions the sample docs can actually answer, with a short
# reference for each so RAGAS has something to compare against.
# ---------------------------------------------------------------------------
TEST_CASES: list[dict[str, str]] = [
    {
        "question": "What is the right to erasure under GDPR Article 17?",
        "reference": (
            "GDPR Article 17 gives data subjects the right to obtain erasure of "
            "personal data concerning them without undue delay when the data is "
            "no longer necessary for the purposes for which it was collected. "
            "The controller has an obligation to erase the data."
        ),
    },
    {
        "question": "What are the principles for processing personal data under GDPR Article 5?",
        "reference": (
            "Personal data must be processed lawfully, fairly and transparently; "
            "collected for specified explicit purposes; limited to what is necessary; "
            "kept accurate and up to date; kept only as long as necessary; and "
            "processed with appropriate security."
        ),
    },
    {
        "question": "When is processing of personal data lawful under GDPR?",
        "reference": (
            "Processing is lawful when: the data subject has given consent; it is "
            "necessary for a contract; for compliance with a legal obligation; to "
            "protect vital interests; for a task in the public interest; or for "
            "the legitimate interests of the controller."
        ),
    },
    {
        "question": "What is the right to data portability under GDPR?",
        "reference": (
            "Under GDPR Article 20, data subjects have the right to receive their "
            "personal data in a structured, commonly used, machine-readable format "
            "and to transmit it to another controller without hindrance."
        ),
    },
    {
        "question": "What security measures does GDPR require for processing personal data?",
        "reference": (
            "GDPR Article 32 requires appropriate technical and organisational "
            "measures, including pseudonymisation and encryption; ability to ensure "
            "ongoing confidentiality, integrity, availability and resilience; ability "
            "to restore access after an incident; and regular testing of those measures."
        ),
    },
    {
        "question": "How does HIPAA define Protected Health Information (PHI)?",
        "reference": (
            "PHI is individually identifiable health information held or transmitted "
            "by a covered entity or its business associate, in any form or medium, "
            "that relates to the individual's health, care, or payment for care."
        ),
    },
    {
        "question": "What administrative safeguards does HIPAA require?",
        "reference": (
            "HIPAA administrative safeguards include security management processes, "
            "assigned security responsibility, workforce security and training, "
            "information access management, security awareness, and contingency planning."
        ),
    },
    {
        "question": "What are the SOC 2 Trust Service Criteria?",
        "reference": (
            "The five SOC 2 Trust Service Criteria are Security, Availability, "
            "Processing Integrity, Confidentiality, and Privacy."
        ),
    },
    {
        "question": "What logical access controls does SOC 2 require?",
        "reference": (
            "SOC 2 requires controls over user access management, authentication, "
            "authorization, and access provisioning and de-provisioning to prevent "
            "unauthorized access to system resources."
        ),
    },
    {
        "question": "What information must a data controller provide when collecting personal data?",
        "reference": (
            "The controller must provide the identity of the controller, the purposes "
            "and legal basis for processing, the recipients of the data, retention "
            "period, and information about the data subject's rights including access, "
            "rectification, erasure, and lodging complaints."
        ),
    },
]


# ---------------------------------------------------------------------------
# Prediction gathering
# ---------------------------------------------------------------------------
def collect_predictions(agent, retriever, test_cases):
    """Run the agent on each case and return rows keyed for the RAGAS dataset."""
    rows = []
    for i, tc in enumerate(test_cases, 1):
        q = tc["question"]
        logger.info(f"[{i}/{len(test_cases)}] {q}")
        try:
            result = agent.run(q)
            answer = (result.get("answer") or "").strip()
            sources = result.get("sources") or []
            contexts = [s.get("content", "") for s in sources if s.get("content")]
            if not contexts:
                docs = retriever.retrieve(q, top_k=5, strategy="hybrid")
                contexts = [d.get("content", "") for d in docs if d.get("content")]
        except Exception as e:
            logger.exception(f"Agent failed on: {q}")
            answer, contexts = f"[error: {e}]", []

        rows.append({
            "question": q,
            "answer": answer or "[empty]",
            "contexts": contexts or ["[no context retrieved]"],
            "reference": tc["reference"],
        })
    return rows


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_with_ragas(rows):
    """Wrap rows in a HF Dataset and run RAGAS evaluate() with our OpenAI wrappers."""
    dataset = Dataset.from_list(rows)

    llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    return evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=False,
    )


def summarize(result) -> dict[str, float]:
    """Extract mean scores per metric from a RAGAS result, tolerating API drift."""
    scores: dict[str, float] = {}
    metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

    df = None
    try:
        df = result.to_pandas()
    except Exception:
        pass

    for m in metric_names:
        val: float | None = None
        # Preferred: aggregate attribute / dict access
        try:
            v = result[m]
            if v is not None:
                val = float(v)
        except Exception:
            pass
        # Fallback: mean of the per-row column
        if val is None and df is not None and m in df.columns:
            try:
                val = float(df[m].dropna().mean())
            except Exception:
                pass
        if val is not None:
            scores[m] = round(val, 3)

    return scores


def print_summary(scores: dict[str, float], num_cases: int) -> None:
    print("\n" + "=" * 60)
    print(f"RAGAS scores  (n = {num_cases})")
    print("=" * 60)
    for k in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        v = scores.get(k)
        print(f"  {k:<22}  {v if v is not None else '(n/a)'}")

    print("\nMarkdown for the README:\n")
    print("| Metric | Score |")
    print("|---|---|")
    print(f"| Faithfulness       | {scores.get('faithfulness', 'n/a')} |")
    print(f"| Answer Relevancy   | {scores.get('answer_relevancy', 'n/a')} |")
    print(f"| Context Precision  | {scores.get('context_precision', 'n/a')} |")
    print(f"| Context Recall     | {scores.get('context_recall', 'n/a')} |")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("RAGAS Evaluation - Agentic Compliance Auditor")
    print("=" * 60)

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set (checked .env at project root).")
        return 1

    print("\nSetting up retriever + agent...")
    chroma_dir = str(PROJECT_ROOT / "data" / "chroma_db")
    vector_store = VectorStore(
        persist_directory=chroma_dir,
        collection_name="compliance_documents",
    )
    retriever = CitationRetriever(vector_store)
    tools = create_langchain_tools(retriever)
    agent = ComplianceAgent(
        retriever=retriever,
        tools=tools,
        model_name="gpt-4o-mini",
        max_iterations=2,
        enable_reflection=False,  # Faster; we're measuring retrieval + generation quality.
    )

    print(f"\nRunning agent on {len(TEST_CASES)} test cases...")
    rows = collect_predictions(agent, retriever, TEST_CASES)

    print("\nScoring with RAGAS (this makes multiple LLM calls per metric)...")
    result = score_with_ragas(rows)

    scores = summarize(result)
    print_summary(scores, num_cases=len(TEST_CASES))

    # Persist
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small",
        "collection": "compliance_documents",
        "num_test_cases": len(TEST_CASES),
        "scores": scores,
        "predictions": rows,
    }
    json_path = docs_dir / "ragas_report.json"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nJSON report -> {json_path}")

    try:
        df = result.to_pandas()
        csv_path = docs_dir / "ragas_report.csv"
        df.to_csv(csv_path, index=False)
        print(f"Per-case CSV -> {csv_path}")
    except Exception:
        pass

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
