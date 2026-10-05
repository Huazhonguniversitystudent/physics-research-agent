import json
import os
from typing import Any

from src.tools.data_sources import redact_result
from src.tools.scientific_data import PROJECT_ROOT, calculate_switching_time, plot_dataset


PUBLIC_TOOL_NAMES = frozenset({
    "search_knowledge_base", "list_knowledge_papers", "inspect_paper",
    "calculator", "electron_energy_from_voltage", "list_datasets",
    "inspect_dataset", "calculate_switching_time", "plot_dataset",
})
PUBLIC_DATASET = "synthetic_micromagnetics.csv"
PUBLIC_DATASET_NAMES = frozenset({PUBLIC_DATASET, f"examples/{PUBLIC_DATASET}", f"data/examples/{PUBLIC_DATASET}"})
SENSITIVE_ARGUMENTS = frozenset({"api_key", "token", "secret", "password", "authorization"})


def is_public_demo_mode(environment: dict[str, str] | None = None) -> bool:
    value = (environment if environment is not None else os.environ).get("PHYSICS_AGENT_PUBLIC_DEMO", "1")
    return value.strip().lower() not in ("0", "false", "off", "no")


def public_tool_schemas(tools: list[dict]) -> list[dict]:
    return [tool for tool in tools if tool["name"] in PUBLIC_TOOL_NAMES]


def validate_public_tool_call(name: str, arguments: dict[str, Any]) -> None:
    if name not in PUBLIC_TOOL_NAMES:
        raise ValueError("Public Demo Mode 禁止访问私人科研数据工具。")
    dataset = arguments.get("dataset")
    if dataset is not None and dataset not in PUBLIC_DATASET_NAMES:
        raise ValueError("Public Demo Mode 只允许公开合成数据集。")
    if name == "search_knowledge_base" and arguments.get("scope", "all") not in ("all", "project_docs", "papers"):
        raise ValueError("Public Demo Mode 的知识范围不合法。")


def public_datasets() -> list[dict]:
    path = PROJECT_ROOT / "data/examples" / PUBLIC_DATASET
    return [{
        "dataset": PUBLIC_DATASET,
        "path": f"data/examples/{PUBLIC_DATASET}",
        "source": "examples",
        "synthetic": True,
        "data_note": "合成流程演示；列名不代表实际运行过模拟软件。",
        "size_bytes": path.stat().st_size,
    }] if path.is_file() else []


def _safe_value(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "…"
    if isinstance(value, dict):
        return {key: "[隐藏]" if key.lower() in SENSITIVE_ARGUMENTS else _safe_value(item, depth + 1)
                for key, item in list(value.items())[:12]}
    if isinstance(value, list):
        return [_safe_value(item, depth + 1) for item in value[:6]]
    if isinstance(value, str):
        redacted = redact_result(value)
        return redacted[:240] + ("…" if len(redacted) > 240 else "")
    return value


def summarize_result(name: str, result: Any) -> tuple[Any, list[str]]:
    citations = []
    if isinstance(result, dict) and name == "search_knowledge_base":
        citations = [item["citation"] for item in result.get("results", [])]
        summary = {
            "found": result.get("found", False),
            "result_count": len(result.get("results", [])),
            "top_score": result.get("top_score", 0),
            "query_coverage": result.get("query_coverage", 0),
            "citations": citations,
        }
    elif name == "list_knowledge_papers" and isinstance(result, list):
        summary = [{key: item.get(key) for key in ("paper_id", "title", "year", "local_available")} for item in result]
    elif isinstance(result, dict):
        keep = ("error", "dataset", "path", "synthetic", "time", "time_unit", "difference", "earlier",
                "page_count", "extractable_pages", "total_characters", "paper_id", "title", "rows", "columns")
        summary = {key: result[key] for key in keep if key in result}
        if not summary:
            summary = {"status": "工具已完成", "result_type": "object"}
    elif isinstance(result, list):
        summary = {"item_count": len(result)}
    else:
        summary = result
    return _safe_value(summary), citations


def sanitize_trace(trace: list[dict]) -> list[dict]:
    safe = []
    for item in trace:
        result, citations = summarize_result(item.get("tool", ""), item.get("result"))
        safe.append({
            "tool": str(item.get("tool", ""))[:80],
            "arguments": _safe_value(item.get("arguments", {})),
            "result": result,
            "citations": item.get("citations", citations)[:8],
        })
    return safe


def synthetic_demo() -> dict:
    dataset = f"data/examples/{PUBLIC_DATASET}"
    first = calculate_switching_time(dataset, "time_ps", "mumax3_mz")
    second = calculate_switching_time(dataset, "time_ps", "comsol_mz")
    plot = plot_dataset(dataset, "time_ps", ["mumax3_mz", "comsol_mz"], "web_synthetic_switching")
    return {
        "dataset": PUBLIC_DATASET,
        "synthetic": True,
        "mumax3_ps": first["switching_time"],
        "comsol_ps": second["switching_time"],
        "difference_ps": abs(first["switching_time"] - second["switching_time"]),
        "plot_path": plot["path"],
        "method": "首次负到正过零，相邻点线性插值",
    }


def trace_as_json(trace: list[dict]) -> str:
    return json.dumps(sanitize_trace(trace), ensure_ascii=False, indent=2)
