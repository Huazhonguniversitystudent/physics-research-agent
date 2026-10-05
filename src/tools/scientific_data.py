import re
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from src.tools.curve_analysis import detect_time_unit, find_zero_crossing, numeric_columns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
PLOTS_DIR = PROJECT_ROOT / "outputs/plots"
SOURCES = ("examples", "local")


def _resolve_dataset(dataset: str) -> Path:
    if not isinstance(dataset, str) or not dataset.strip():
        raise ValueError("请提供 CSV 数据集名称。")
    if "\\" in dataset or ":" in dataset or Path(dataset).is_absolute():
        raise ValueError("只允许数据目录内的相对 CSV 路径。")
    parts = dataset.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("数据路径不能包含路径穿越。")
    if parts[0] == "data":
        parts = parts[1:]
    if len(parts) == 1:
        candidates = [DATA_ROOT / source / parts[0] for source in SOURCES]
    elif len(parts) == 2 and parts[0] in SOURCES:
        candidates = [DATA_ROOT.joinpath(*parts)]
    else:
        raise ValueError("数据路径必须位于 data/examples 或 data/local 允许目录。")

    matches = []
    for candidate in candidates:
        path = candidate.resolve()
        if not any(path.is_relative_to(DATA_ROOT / source) for source in SOURCES):
            raise ValueError("数据路径解析后逃离了允许目录。")
        if path.suffix.lower() != ".csv":
            raise ValueError("只允许读取 CSV 文件。")
        if path.is_file():
            matches.append(path)
    if not matches:
        raise ValueError("数据集不存在，请先调用 list_datasets。")
    if len(matches) > 1:
        raise ValueError("存在同名数据集，请指定 examples/文件名或 local/文件名。")
    return matches[0]


def _metadata(path: Path) -> dict:
    source = path.relative_to(DATA_ROOT).parts[0]
    return {
        "dataset": path.name,
        "path": f"data/{source}/{path.name}",
        "source": source,
        "synthetic": source == "examples" and path.name.startswith("synthetic_"),
        "data_note": (
            "合成流程演示；列名不代表实际运行过模拟软件。"
            if source == "examples" and path.name.startswith("synthetic_")
            else "用户提供的数据；未验证真实性。"
        ),
    }


def _read_dataset(dataset: str) -> tuple[Path, pd.DataFrame]:
    path = _resolve_dataset(dataset)
    try:
        frame = pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise ValueError("无法读取 CSV，请检查文件编码、内容格式和访问权限。") from exc
    return path, frame


def list_datasets() -> list[dict]:
    """List only accessible CSVs, without exposing absolute user paths."""
    datasets = []
    for source in SOURCES:
        for candidate in sorted((DATA_ROOT / source).glob("*.csv")):
            try:
                path = _resolve_dataset(f"{source}/{candidate.name}")
            except ValueError:
                continue
            datasets.append({**_metadata(path), "size_bytes": path.stat().st_size})
    return datasets


def inspect_dataset(dataset: str) -> dict:
    path, frame = _read_dataset(dataset)
    preview = frame.head(5).astype(object)
    preview = preview.where(pd.notna(preview), None)
    return {
        **_metadata(path),
        "rows": len(frame),
        "column_count": len(frame.columns),
        "columns": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "preview": preview.to_dict(orient="records"),
        "missing_values": {column: int(count) for column, count in frame.isna().sum().items()},
    }


def calculate_switching_time(
    dataset: str,
    time_column: str,
    mz_column: str,
    direction: str = "negative_to_positive",
) -> dict:
    path, frame = _read_dataset(dataset)
    return {
        **_metadata(path),
        "time_column": time_column,
        "mz_column": mz_column,
        "time_unit": detect_time_unit(time_column),
        **find_zero_crossing(frame, time_column, mz_column, direction),
    }


def plot_dataset(dataset: str, x_column: str, y_columns: list[str], output_name: str) -> dict:
    if not isinstance(y_columns, list) or not y_columns or not all(isinstance(column, str) for column in y_columns):
        raise ValueError("y_columns 必须是非空列名列表。")
    if not isinstance(output_name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.png)?", output_name):
        raise ValueError("输出名只允许字母、数字、下划线、连字符和可选的 .png 后缀。")
    filename = output_name if output_name.endswith(".png") else f"{output_name}.png"
    output = (PLOTS_DIR / filename).resolve()
    if not output.is_relative_to(PLOTS_DIR):
        raise ValueError("输出路径解析后逃离了允许目录。")

    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", dataset):
        from src.tools.micromagnetics import load_normalized_dataset
        frame, metadata = load_normalized_dataset(dataset, x_column, y_columns)
        curves = [(group.sort_values("time"), "time", "mz", label) for label, group in frame.groupby("source", sort=False)]
        unit = metadata["time_unit"]
        x_label = f"Time ({unit})" if unit != "unknown" else "Time (unit unknown)"
        y_label = "<mz>"
        title = f"{'SYNTHETIC demo' if metadata['synthetic'] else 'Registered data'}: {dataset}"
    else:
        path, frame = _read_dataset(dataset)
        columns = list(dict.fromkeys([x_column, *y_columns]))
        numeric = numeric_columns(frame, columns).sort_values(x_column, kind="stable")
        metadata = _metadata(path)
        curves = [(numeric, x_column, column, column) for column in y_columns]
        x_label = {"time_ps": "Time (ps)", "time_ns": "Time (ns)"}.get(x_column, x_column)
        y_label = "<mz>" if all("mz" in column or "m_z" in column for column in y_columns) else ", ".join(y_columns)
        title = f"{'SYNTHETIC demo: ' if metadata['synthetic'] else ''}{path.name}"
    if frame.empty:
        raise ValueError("CSV 没有数据，无法绘图。")
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots()
    try:
        for values, x, y, label in curves:
            ax.plot(values[x], values[y], label=label)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(output, dpi=150)
    finally:
        plt.close(fig)

    return {
        **metadata,
        "dataset_path": metadata.get("path", dataset),
        "path": f"outputs/plots/{filename}",
        "x_column": x_column,
        "y_columns": y_columns,
        "rows": len(frame),
    }
