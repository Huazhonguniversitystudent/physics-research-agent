import csv
import io
import json
import re
from pathlib import Path

import pandas as pd


CONFIG_FILE = Path(__file__).resolve().parents[2] / "config/data_sources.local.json"
ALIAS_PATTERN = r"[A-Za-z][A-Za-z0-9_-]{0,63}"


def redact_private_paths(value):
    if not isinstance(value, str):
        return value
    value = re.sub(r"(?:[A-Za-z]:[\\/]|\\\\)[^\n\r\"<>]*", "[本地路径已隐藏]", value)
    return re.sub(r"(?<![\w:])/(?:home|Users|mnt|tmp|private|etc|root)/[^\n\r\"<>]*", "[本地路径已隐藏]", value)


def redact_result(value):
    if isinstance(value, dict):
        return {redact_private_paths(key): redact_result(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_result(item) for item in value]
    return redact_private_paths(value)


def _registry() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        registry = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("本地数据注册表无法读取，请检查 JSON 格式和权限。") from exc
    if not isinstance(registry, dict):
        raise ValueError("本地数据注册表必须是 alias 到数据源配置的对象。")
    for name, entry in registry.items():
        if not re.fullmatch(ALIAS_PATTERN, name) or not isinstance(entry, dict):
            raise ValueError("本地数据注册表包含无效 alias 或配置。")
    return registry


def get_external_entry(dataset_name: str) -> dict:
    if not isinstance(dataset_name, str) or not re.fullmatch(ALIAS_PATTERN, dataset_name):
        raise ValueError("外部数据集只接受注册 alias，不接受路径。")
    registry = _registry()
    if dataset_name not in registry:
        raise ValueError("数据集未注册，请先调用 list_external_datasets 或配置本地注册表。")
    return registry[dataset_name]


def _registered_path(entry: dict) -> Path:
    value = entry.get("path")
    if not isinstance(value, str):
        raise ValueError("该数据源没有单文件路径，请按组合曲线分析。")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".csv":
        raise ValueError("注册表路径必须是明确的绝对 CSV 文件路径。")
    resolved = path.resolve()
    if resolved != path.absolute():
        raise ValueError("注册文件的最终路径发生偏移，请直接注册真实文件而非符号链接。")
    return resolved


def list_external_datasets() -> list[dict]:
    registry = _registry()
    result = []
    for name, entry in registry.items():
        members = entry.get("datasets", [name])
        exists = False
        if isinstance(members, list) and members:
            try:
                exists = all(member in registry and _registered_path(registry[member]).is_file() for member in members)
            except (ValueError, OSError):
                pass
        result.append({
            "name": name,
            "type": redact_private_paths(entry.get("type", "csv")),
            "description": redact_private_paths(entry.get("description", "")),
            "exists": exists,
            "synthetic": bool(entry.get("synthetic", False)),
        })
    return result


def _read_csv(path: Path) -> tuple[pd.DataFrame, dict]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError("注册的数据文件不存在或不可读取。") from exc
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "gbk"
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            raise ValueError("CSV 编码无法识别，请使用 UTF-8、UTF-8 BOM 或 GBK/CP936。") from exc
    text = text.lstrip("\r\n")
    # Native MuMax-style tabular headers may begin with '# '.
    if text.startswith("# "):
        text = text[2:]
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;")
        delimiter = dialect.delimiter
    except csv.Error:
        header = text.splitlines()[0] if text.strip() else ""
        delimiter = max((",", "\t", ";"), key=header.count)
    try:
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter, strict=True))
        if not rows or not rows[0] or any(row and len(row) != len(rows[0]) for row in rows[1:]):
            raise ValueError("CSV 表头或数据行列数不一致。")
        if any(not name.strip() for name in rows[0]) or len(set(rows[0])) != len(rows[0]):
            raise ValueError("CSV 表头包含空列名或重复列名。")
        frame = pd.read_csv(io.StringIO(text), sep=delimiter)
    except (csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError("CSV 格式无效，请检查分隔符、引号和表头。") from exc
    return frame, {"detected_delimiter": delimiter, "detected_encoding": encoding}


def load_external_dataset(dataset_name: str) -> tuple[pd.DataFrame, dict]:
    entry = get_external_entry(dataset_name)
    path = _registered_path(entry)
    frame, format_info = _read_csv(path)
    return frame, {
        "dataset": dataset_name,
        "filename": path.name,
        "source": "external",
        "synthetic": bool(entry.get("synthetic", False)),
        "data_note": "合成测试数据。" if entry.get("synthetic", False) else "用户注册的本地科研数据；不代表已独立验证物理正确性。",
        **format_info,
    }


def inspect_external_dataset(dataset_name: str) -> dict:
    from src.tools.micromagnetics import detect_micromagnetic_columns, load_normalized_dataset

    entry = get_external_entry(dataset_name)
    if "datasets" in entry:
        frame, metadata = load_normalized_dataset(dataset_name)
        detected = {"time_column": "time", "mz_columns": ["mz"], "source_column": "source"}
    else:
        frame, metadata = load_external_dataset(dataset_name)
        try:
            detected = detect_micromagnetic_columns(frame)
        except ValueError:
            detected = {"note": "不能可靠识别时间/磁化列，请显式指定；该文件也可能只是汇总表。"}
    preview = frame.head(3).astype(object).where(pd.notna(frame.head(3)), None)
    preview = preview.map(redact_private_paths)
    return redact_result({
        **metadata,
        "rows": len(frame),
        "columns": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_values": {column: int(count) for column, count in frame.isna().sum().items()},
        "preview": preview.to_dict(orient="records"),
        "detected_columns": detected,
    })
