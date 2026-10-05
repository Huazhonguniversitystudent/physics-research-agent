"""Shared numerical operations for local and registered CSV curves."""

import math
import re

import pandas as pd


def detect_time_unit(column: str) -> str:
    match = re.search(r"(?:_|\(|\[|\s)(ps|ns|s)\s*[)\]]?\s*$", column, re.IGNORECASE)
    return match.group(1).lower() if match else "unknown"


def numeric_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"列不存在：{column}")
    try:
        numeric = frame[columns].apply(pd.to_numeric, errors="raise").astype(float)
    except (ValueError, TypeError) as exc:
        raise ValueError("选定列包含非数值数据。") from exc
    if not all(math.isfinite(value) for value in numeric.to_numpy().flat):
        raise ValueError("选定列包含 NaN、缺失值或无穷值，无法可靠分析。")
    return numeric


def prepare_curve(frame: pd.DataFrame, time_column: str, value_column: str) -> tuple[pd.DataFrame, bool]:
    if time_column == value_column:
        raise ValueError("时间列和数值列必须不同。")
    if frame.empty:
        raise ValueError("没有数据，无法分析曲线。")
    numeric = numeric_columns(frame, [time_column, value_column])
    was_sorted = not numeric[time_column].is_monotonic_increasing
    numeric = numeric.sort_values(time_column, kind="stable")
    if numeric[time_column].duplicated().any():
        raise ValueError("时间列存在重复采样时间，无法唯一确定 crossing。")
    return numeric, was_sorted


def find_crossings(frame: pd.DataFrame, time_column: str, mz_column: str, direction: str = "negative_to_positive") -> dict:
    if direction not in ("negative_to_positive", "positive_to_negative"):
        raise ValueError("direction 必须为 negative_to_positive 或 positive_to_negative。")
    if len(frame) < 2:
        raise ValueError("计算 crossing 至少两行数据。")
    numeric, was_sorted = prepare_curve(frame, time_column, mz_column)
    samples = list(numeric.itertuples(index=False, name=None))
    crossings = []
    for (t1, m1), (t2, m2) in zip(samples, samples[1:]):
        crossed = (m1 < 0 <= m2) if direction == "negative_to_positive" else (m1 > 0 >= m2)
        if crossed:
            crossings.append({
                "switching_time": t1 + (0 - m1) * (t2 - t1) / (m2 - m1),
                "bracket": {"t1": t1, "mz1": m1, "t2": t2, "mz2": m2},
            })
    return {
        "crossings": crossings,
        "direction": direction,
        "sorted": was_sorted,
        "sorting_note": "已按时间重新排序。" if was_sorted else "输入时间已递增，无需重新排序。",
        "method": "linear_interpolation",
    }


def find_zero_crossing(frame: pd.DataFrame, time_column: str, mz_column: str, direction: str = "negative_to_positive") -> dict:
    result = find_crossings(frame, time_column, mz_column, direction)
    crossings = result.pop("crossings")
    if not crossings:
        raise ValueError("未找到指定方向的零点 crossing，无法确定翻转时间。")
    return {**result, **crossings[0]}
