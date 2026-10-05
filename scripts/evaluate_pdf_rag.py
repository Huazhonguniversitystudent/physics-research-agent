import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.retriever import KnowledgeRetriever, load_knowledge_documents


def evaluate_cases(cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        retriever = KnowledgeRetriever(load_knowledge_documents("papers", case["paper_id"]))
        if not retriever.chunks:
            raise ValueError("评估论文本地不可用，不能将空索引记为负例通过。")
        result = retriever.search(case["question"], 4)
        pages = [item["page_number"] for item in result["results"]]
        positive = bool(case["acceptable_pages"])
        passed = bool(set(pages).intersection(case["acceptable_pages"])) if positive else not result["found"]
        rows.append({**case, "positive": positive, "passed": passed, "returned_pages": pages,
                     "top_score": result["top_score"], "query_coverage": result["query_coverage"],
                     "keyword_hits": sorted({word for word in case["keywords"] for item in result["results"] if word.lower() in item["text"].lower()})})
    positives = [row for row in rows if row["positive"]]
    negatives = [row for row in rows if not row["positive"]]
    return {"metric_note": "仅评估页命中与检索拒绝，不是 LLM accuracy，也不是 claim entailment。关键词仅作诊断。",
            "top_k": 4, "positive_hits": sum(row["passed"] for row in positives), "positive_cases": len(positives),
            "page_hit_at_4": sum(row["passed"] for row in positives) / len(positives),
            "negative_rejections": sum(row["passed"] for row in negatives), "negative_cases": len(negatives),
            "negative_rejection_rate": sum(row["passed"] for row in negatives) / len(negatives), "cases": rows}


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[1] / "tests/pdf_eval_cases.json"
    report = evaluate_cases(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not all(row["passed"] for row in report["cases"]):
        raise SystemExit(1)
