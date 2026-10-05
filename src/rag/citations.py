import re


def make_citation(source: str, start_line: int, end_line: int) -> str:
    return f"[{source}:L{start_line}-L{end_line}]"


def validate_answer_citations(answer: str, allowed_citations: set[str]) -> dict:
    citations = re.findall(r"\[[^\]\r\n]+:L\d+-L\d+\]", answer)
    invalid = [citation for citation in citations if citation not in allowed_citations]
    missing = bool(allowed_citations) and not citations
    return {"valid": not invalid and not missing, "invalid": invalid, "missing": missing}
