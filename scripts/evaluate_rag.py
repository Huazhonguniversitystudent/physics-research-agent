import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.documents import load_documents
from src.rag.retriever import KnowledgeRetriever


def evaluate_cases(retriever: KnowledgeRetriever, cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        result = retriever.search(case["query"])
        sources = {item["source"] for item in result["results"]}
        expected = case.get("expected_sources", [])
        passed = bool(sources.intersection(expected)) if expected else not result["found"]
        rows.append({"query": case["query"], "passed": passed, "top_score": result["top_score"], "query_coverage": result["query_coverage"], "sources": sorted(sources), "positive": bool(expected)})
    positives = [row for row in rows if row["positive"]]
    negatives = [row for row in rows if not row["positive"]]
    return {
        "documents": retriever.document_count, "chunks": len(retriever.chunks),
        "threshold": retriever.threshold, "top_k": 4,
        "positive_hits": sum(row["passed"] for row in rows if row["positive"]),
        "positive_cases": sum(row["positive"] for row in rows),
        "negative_rejections": sum(row["passed"] for row in rows if not row["positive"]),
        "negative_cases": sum(not row["positive"] for row in rows),
        "recall_at_4": sum(row["passed"] for row in positives) / len(positives) if positives else None,
        "negative_rejection_rate": sum(row["passed"] for row in negatives) / len(negatives) if negatives else None,
        "cases": rows,
    }


def main() -> None:
    path = Path(__file__).resolve().parents[1] / "tests/rag_eval_cases.json"
    result = evaluate_cases(KnowledgeRetriever(load_documents()), json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(case["passed"] for case in result["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
