import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent import run_agent
from src.rag.citations import validate_answer_citations
from src.rag.retriever import search_knowledge_base


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests/holdout_eval_cases.json"
REPORT_PATH = ROOT / "outputs/day7_holdout_report.json"


def tool_family(trace: list[dict]) -> str:
    for item in trace:
        if item["tool"] == "calculator":
            return "calculator"
        if item["tool"] == "search_knowledge_base":
            scope = item.get("arguments", {}).get("scope", "all")
            if scope == "papers":
                return "papers"
            if scope == "project_docs":
                return "project_docs"
    return "normal" if not trace else "other"


def evaluate_retrieval(cases: list[dict]) -> dict:
    rows = []
    for case in cases:
        category = case["category"]
        if category == "project_docs":
            result = search_knowledge_base(case["query"], top_k=4, scope="project_docs", public_only=True)
            returned = sorted({item["source"] for item in result["results"]})
            passed = bool(set(returned).intersection(case["expected_sources"]))
            rows.append({"id": case["id"], "category": category, "passed": passed,
                         "returned_sources": returned, "citations": [item["citation"] for item in result["results"]]})
        elif category == "pdf":
            result = search_knowledge_base(case["query"], top_k=4, scope="papers",
                                           paper_id=case["paper_id"], public_only=True)
            returned = [item["page_number"] for item in result["results"]]
            passed = bool(set(returned).intersection(case["acceptable_pages"]))
            rows.append({"id": case["id"], "category": category, "passed": passed,
                         "returned_pages": returned, "citations": [item["citation"] for item in result["results"]]})
        elif category == "negative":
            result = search_knowledge_base(case["query"], top_k=4, scope=case["scope"],
                                           paper_id=case.get("paper_id"), public_only=True)
            rows.append({"id": case["id"], "category": category, "passed": not result["found"],
                         "found": result["found"], "citations": [item["citation"] for item in result["results"]]})
    return {"rows": rows}


def evaluate_agent(cases: list[dict]) -> dict:
    rows = []
    selected = [case for case in cases if case["category"] in ("routing", "project_docs", "pdf")]
    for case in selected:
        try:
            result = run_agent(case["query"], show_steps=False, public_mode=True, collect_trace=True)
            citations = {citation for item in result["trace"] for citation in item.get("citations", [])}
            validation = validate_answer_citations(result["answer"], citations) if citations else {
                "valid": True, "invalid": [], "missing": False
            }
            row = {"id": case["id"], "category": case["category"], "answer": result["answer"],
                   "trace": result["trace"], "citation_validation": validation}
            if case["category"] == "routing":
                actual = tool_family(result["trace"])
                row.update({"expected_tool_family": case["expected_tool_family"], "actual_tool_family": actual,
                            "routing_passed": actual == case["expected_tool_family"]})
            rows.append(row)
        except Exception as exc:
            rows.append({"id": case["id"], "category": case["category"], "error": type(exc).__name__,
                         "message": str(exc)[:300], "citation_validation": {"valid": False}})
    return {"rows": rows}


def ratio(numerator: int, denominator: int) -> dict:
    return {"passed": numerator, "total": denominator, "rate": numerator / denominator if denominator else None}


def build_metrics(retrieval: dict, agent: dict) -> dict:
    retrieval_rows = retrieval["rows"]
    routes = [row for row in agent["rows"] if row["category"] == "routing"]
    docs = [row for row in retrieval_rows if row["category"] == "project_docs"]
    pdf = [row for row in retrieval_rows if row["category"] == "pdf"]
    negatives = [row for row in retrieval_rows if row["category"] == "negative"]
    generated = [row for row in agent["rows"] if row["category"] in ("project_docs", "pdf")]
    valid = sum(row.get("citation_validation", {}).get("valid", False) for row in generated)
    return {
        "routing": ratio(sum(row.get("routing_passed", False) for row in routes), len(routes)),
        "project_docs_source_hit_at_4": ratio(sum(row["passed"] for row in docs), len(docs)),
        "pdf_page_hit_at_4": ratio(sum(row["passed"] for row in pdf), len(pdf)),
        "negative_rejection": ratio(sum(row["passed"] for row in negatives), len(negatives)),
        "generated_answer_citation_validity": ratio(valid, len(generated)),
        "manual_grounding": "Pending manual Supported/Partially Supported/Unsupported labels for the 8 generated answers.",
    }


def main() -> None:
    raw = CASES_PATH.read_bytes()
    cases = json.loads(raw.decode("utf-8"))
    digest = hashlib.sha256(raw).hexdigest()
    print(f"holdout SHA256: {digest}")
    print(f"holdout cases: {len(cases)}")
    retrieval = evaluate_retrieval(cases)
    agent = evaluate_agent(cases)
    report = {"holdout_sha256": digest, "case_count": len(cases),
              "discipline": "Fixed before this formal run; results were not used to tune retrieval.",
              "metrics": build_metrics(retrieval, agent), "retrieval": retrieval, "agent": agent}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    print(f"full report: {REPORT_PATH.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
