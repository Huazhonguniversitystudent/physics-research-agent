import math
import re

import pandas as pd

from src.tools.curve_analysis import detect_time_unit, find_crossings, find_zero_crossing, numeric_columns, prepare_curve
from src.tools.data_sources import get_external_entry, load_external_dataset, redact_private_paths


TIME_NAMES = ("time", "Time", "t", "time_ps", "time_ns", "time_s", "Time (ps)", "Time (ns)", "Time (s)")
MZ_NAMES = ("mz", "m_z", "<mz>", "M_z", "average_mz", "avg_mz", "mumax3_mz", "comsol_mz")
UNIT_SCALE = {"s": 1.0, "ns": 1e-9, "ps": 1e-12}


def _matching_columns(columns, names) -> list[str]:
    exact = [column for column in columns if column in names]
    if exact:
        return exact
    normalize = lambda value: re.sub(r"[^a-z0-9]", "", value.lower())
    known = {normalize(name) for name in names}
    return [column for column in columns if normalize(column) in known]


def _time_column(frame: pd.DataFrame) -> str:
    candidates = _matching_columns(frame.columns, TIME_NAMES)
    if len(candidates) != 1:
        raise ValueError("无法唯一识别时间列，请显式指定 time_column。")
    return candidates[0]


def detect_micromagnetic_columns(frame: pd.DataFrame) -> dict:
    time_column = _time_column(frame)
    mz_columns = _matching_columns(frame.columns, MZ_NAMES)
    if not mz_columns:
        raise ValueError("无法可靠识别磁化列，请显式指定 mz_columns。")
    return {"time_column": time_column, "mz_columns": mz_columns, "time_unit": detect_time_unit(time_column)}


def load_normalized_dataset(
    dataset_name: str,
    time_column: str | None = None,
    mz_columns: list[str] | None = None,
    time_unit: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Normalize each curve independently; never align or resample native grids."""
    if time_unit is not None and time_unit not in (*UNIT_SCALE, "unknown"):
        raise ValueError("时间单位必须为 s、ns、ps 或 unknown。")
    entry = get_external_entry(dataset_name)
    composite = "datasets" in entry
    members = entry.get("datasets", [dataset_name])
    if not isinstance(members, list) or not members or not all(isinstance(name, str) for name in members):
        raise ValueError("组合注册表的 datasets 必须为非空 alias 列表。")
    if composite and (time_column not in (None, "time") or mz_columns not in (None, ["mz"])):
        raise ValueError("组合数据已标准化，使用 time、mz 和 source 列。")

    curves = []
    components = []
    output_unit = time_unit
    for member in members:
        spec = get_external_entry(member)
        if "datasets" in spec:
            raise ValueError("组合成员必须是单文件 alias，不允许嵌套或循环组合。")
        frame, info = load_external_dataset(member)
        time_name = (None if composite else time_column) or spec.get("time_column") or _time_column(frame)
        selected = (None if composite else mz_columns) or spec.get("mz_columns") or _matching_columns(frame.columns, MZ_NAMES)
        if not isinstance(selected, list) or not selected or not all(isinstance(name, str) for name in selected):
            raise ValueError("请显式指定非空 mz_columns 列名列表。")
        if len(set(selected)) != len(selected):
            raise ValueError("不能重复选择同一磁化列。")
        native_unit = detect_time_unit(time_name)
        configured_unit = spec.get("time_unit")
        if configured_unit is not None:
            if configured_unit not in UNIT_SCALE:
                raise ValueError("注册表时间单位必须为 s、ns 或 ps。")
            if native_unit not in ("unknown", configured_unit):
                raise ValueError("注册表单位与列名单位不一致，请检查配置。")
            native_unit = configured_unit
        if output_unit is None:
            output_unit = native_unit
        if native_unit == "unknown" and output_unit != "unknown":
            if time_unit is None:
                raise ValueError("组合包含未知时间单位，请显式确认各数据源单位。")
            factor = 1.0  # Explicit unit supplied for an otherwise unitless input.
        elif native_unit != output_unit:
            if native_unit == "unknown" or output_unit == "unknown":
                raise ValueError("无法将已知单位和 unknown 单位混合比较。")
            factor = UNIT_SCALE[native_unit] / UNIT_SCALE[output_unit]
        else:
            factor = 1.0
        components.append({**info, "original_time_column": time_name, "original_mz_columns": selected, "native_time_unit": native_unit, "rows": len(frame)})
        for mz_name in selected:
            # Validate without reordering here so numerical tools can report sorting.
            if time_name == mz_name:
                raise ValueError("时间列和磁化列必须不同。")
            numeric = numeric_columns(frame, [time_name, mz_name])
            label = spec.get("label", member) if len(selected) == 1 else mz_name
            if not isinstance(label, str) or not label:
                raise ValueError("曲线 label 必须是非空字符串。")
            label = redact_private_paths(label)
            curves.append(pd.DataFrame({"time": numeric[time_name] * factor, "mz": numeric[mz_name], "source": label}))
    labels = [curve["source"].iloc[0] for curve in curves if not curve.empty]
    if len(set(labels)) != len(labels):
        raise ValueError("曲线 source 标签重复，请在注册表设置不同 label。")
    normalized = pd.concat(curves, ignore_index=True)
    synthetic = all(component["synthetic"] for component in components)
    return normalized, {
        "dataset": dataset_name,
        "source": "external",
        "synthetic": synthetic,
        "data_note": "合成测试数据。" if synthetic else "注册的本地原始曲线；独立保留各自采样点，未做预先重采样。",
        "time_unit": output_unit,
        "sources": labels,
        "unit_note": "单位未知，不能擅自解释为 ps。" if output_unit == "unknown" else "列名/本地配置识别单位；显式 time_unit 可转换已知单位或声明未知单位。",
        "components": components,
        "detected_delimiter": "per_component" if composite else components[0]["detected_delimiter"],
        "detected_encoding": "per_component" if composite else components[0]["detected_encoding"],
    }


def compare_switching_times(dataset_name: str, time_column: str | None = None, mz_columns: list[str] | None = None, time_unit: str | None = None) -> dict:
    frame, info = load_normalized_dataset(dataset_name, time_column, mz_columns, time_unit)
    groups = list(frame.groupby("source", sort=False))
    if len(groups) != 2:
        raise ValueError("比较需要恰好两条曲线，请指定两列或注册两个成员。")
    results = [{"label": label, **find_zero_crossing(curve, "time", "mz"), "time_unit": info["time_unit"]} for label, curve in groups]
    first, second = results
    difference = abs(first["switching_time"] - second["switching_time"])
    earlier = "tie" if difference == 0 else min(results, key=lambda item: item["switching_time"])["label"]
    return {**info, "results": results, "earlier": earlier, "difference": difference, "method": "linear_interpolation"}


def _selected_curve(dataset_name, time_column, value_column, source, time_unit):
    frame, info = load_normalized_dataset(dataset_name, time_column, [value_column] if value_column else None, time_unit)
    groups = list(frame.groupby("source", sort=False))
    if source is None and len(groups) != 1:
        raise ValueError("多曲线数据必须用 source 指定曲线标签。")
    chosen = source if source is not None else groups[0][0] if groups else None
    curve = frame[frame["source"] == chosen]
    if curve.empty:
        raise ValueError("source 不存在或曲线为空，请先 inspect 数据。")
    return curve, {**info, "curve_source": chosen}


def _sample(curve: pd.DataFrame, target_time: float, method: str) -> dict:
    if method not in ("nearest", "linear"):
        raise ValueError("采样方法必须为 nearest 或 linear。")
    if isinstance(target_time, bool) or not isinstance(target_time, (int, float)) or not math.isfinite(target_time):
        raise ValueError("target_time 必须是有限数值。")
    numeric, was_sorted = prepare_curve(curve, "time", "mz")
    times, values = numeric["time"].tolist(), numeric["mz"].tolist()
    if not times[0] <= target_time <= times[-1]:
        raise ValueError("目标时间超出数据范围，禁止外推。")
    if method == "nearest" or target_time in times:
        index = min(range(len(times)), key=lambda index: abs(times[index] - target_time))
        return {"value": values[index], "sample_time": times[index], "target_time": target_time, "method": method, "interpolated": False, "sorted": was_sorted}
    for index in range(1, len(times)):
        t1, t2 = times[index - 1], times[index]
        if t1 < target_time < t2:
            value = values[index - 1] + (values[index] - values[index - 1]) * (target_time - t1) / (t2 - t1)
            return {"value": value, "target_time": target_time, "method": method, "interpolated": True, "sorted": was_sorted, "bracket": {"t1": t1, "value1": values[index - 1], "t2": t2, "value2": values[index]}}


def sample_value_at_time(dataset_name: str, time_column: str | None = None, value_column: str | None = None, target_time: float = 100, method: str = "linear", source: str | None = None, time_unit: str | None = None) -> dict:
    curve, info = _selected_curve(dataset_name, time_column, value_column, source, time_unit)
    return {**info, **_sample(curve, target_time, method)}


def summarize_magnetization_curve(dataset_name: str, time_column: str | None = None, mz_column: str | None = None, source: str | None = None, target_time: float | None = None, time_unit: str | None = None) -> dict:
    curve, info = _selected_curve(dataset_name, time_column, mz_column, source, time_unit)
    numeric, was_sorted = prepare_curve(curve, "time", "mz")
    crossings = find_crossings(curve, "time", "mz") if len(curve) >= 2 else {"crossings": []}
    values = numeric["mz"]
    return {
        **info,
        "initial_mz": float(values.iloc[0]),
        "final_mz": float(values.iloc[-1]),
        "min_mz": float(values.min()),
        "max_mz": float(values.max()),
        "crossing_count": len(crossings["crossings"]),
        "crossing_direction": "negative_to_positive",
        "first_switching_time": crossings["crossings"][0]["switching_time"] if crossings["crossings"] else None,
        "sorted": was_sorted,
        "target_time_value": _sample(curve, target_time, "linear") if target_time is not None else None,
    }
