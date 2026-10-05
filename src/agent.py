import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from src.tools.calculator import calculate
from src.tools.physics import electron_energy_from_voltage
from src.tools.data_sources import inspect_external_dataset, list_external_datasets, redact_result
from src.tools.micromagnetics import compare_switching_times, sample_value_at_time, summarize_magnetization_curve
from src.tools.scientific_data import (
    calculate_switching_time,
    inspect_dataset,
    list_datasets,
    plot_dataset,
)


MODEL = "deepseek-flash"
MAX_STEPS = 5

SYSTEM_INSTRUCTIONS = (
    "你是面向物理科研学习者的助手。概念解释应直接回答，不要为了补充数值例子而调用工具。"
    "只有用户明确要求数值结果，或不计算就无法完成任务时，才调用合适的工具；"
    "需要计算时不要心算或编造工具结果。"
    "分析前先检查结构：仓库 CSV 用 inspect_dataset，注册的真实 alias 用 inspect_external_dataset；"
    "不知 alias 时先 list_external_datasets，仓库示例用 list_datasets。外部工具只接受 alias，不返回真实绝对路径。"
    "不得编造数据或列名，缺失数据时明确无法确定；区分合成演示和本地数据。"
    "遵循工具中的 data_note 和 sorting_note；过零时间不代表磁化已达到 +1。"
    "不要推断数据没有支持的物理机制或模拟软件差异。"
    "科研回答包含来源、方法、数值、单位及是否插值；unknown 单位不得猜测。工具已返回的差值无需重复计算。"
    "compare/sample/summarize 仅接收注册 alias；仓库 CSV 用 inspect_dataset、calculate_switching_time、plot_dataset。"
    "不新增工具未返回的百分比或数值；采样行数相同不表示时间点相同。"
    "组合真实曲线统一为 time/mz/source，按 sources 标签分别分析；100 ps 查询显式用 time_unit=ps。"
    "参数已确认的独立工具请求可同轮发出，尽量在 5 轮内完成任务。"
)

TOOLS = [
    {
        "type": "function",
        "name": "calculator",
        "description": "用于执行可靠的数学计算。当问题包含数值计算时优先使用本工具，而不是心算。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "只包含受支持运算符、数学函数和常数的表达式。",
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "electron_energy_from_voltage",
        "description": "用于计算单个电子通过给定电势差获得的能量，返回 eV 和 J。",
        "parameters": {
            "type": "object",
            "properties": {
                "voltage_v": {
                    "type": "number",
                    "description": "电势差，单位为 V。",
                }
            },
            "required": ["voltage_v"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_datasets",
        "description": "列出当前可以分析的科研 CSV 数据集，返回相对路径、大小及合成数据标记。",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "inspect_dataset",
        "description": "在分析科研 CSV 前检查其列名、类型、行数、前 5 行和缺失值。",
        "parameters": {
            "type": "object",
            "properties": {"dataset": {"type": "string", "description": "CSV 文件名或 data/examples、data/local 下的相对路径。"}},
            "required": ["dataset"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "calculate_switching_time",
        "description": "计算 mz 指定方向首次穿过 0 的时间，使用相邻点线性插值；默认负到正。",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "description": "允许目录内的 CSV 名称或相对路径。"},
                "time_column": {"type": "string", "description": "inspect 确认的时间列名，_ps/_ns 后缀用于识别单位。"},
                "mz_column": {"type": "string", "description": "inspect 确认的磁化列名。"},
                "direction": {"type": "string", "enum": ["negative_to_positive", "positive_to_negative"]},
            },
            "required": ["dataset", "time_column", "mz_column"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "plot_dataset",
        "description": "绘制仓库 CSV 或注册外部 alias 的曲线，PNG 保存到 outputs/plots；组合数据使用 time 和 [mz]，自动按 source 分曲线。",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset": {"type": "string", "description": "仓库 CSV 或本地注册的外部 alias；禁止绝对路径。"},
                "x_column": {"type": "string"},
                "y_columns": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "output_name": {"type": "string", "description": "仅字母、数字、下划线、连字符，可带 .png；不能包含路径。"},
            },
            "required": ["dataset", "x_column", "y_columns", "output_name"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_external_datasets",
        "description": "列出用户本地注册的真实科研数据 alias 和是否存在，不返回绝对路径。",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "inspect_external_dataset",
        "description": "分析外部数据前确认 alias 的列、单位、结构、少量预览；组合数据标准化为 time/mz/source。",
        "parameters": {
            "type": "object",
            "properties": {"dataset_name": {"type": "string", "description": "本地注册的 alias，不是路径。"}},
            "required": ["dataset_name"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "compare_switching_times",
        "description": "比较注册数据中的两列或两份组合原始曲线的首次负到正过零时间，线性插值并返回谁更早、差值及单位。",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_name": {"type": "string", "description": "list_external_datasets 中的注册 alias；不是仓库 CSV 文件名或路径。"},
                "time_column": {"type": "string", "description": "可选；组合数据用 time，单文件用 inspect 确认的列名。"},
                "mz_columns": {"type": "array", "items": {"type": "string"}, "description": "可选；单文件选择两列，组合数据用 [mz] 或省略。"},
                "time_unit": {"type": "string", "enum": ["ps", "ns", "s", "unknown"], "description": "可选输出单位，已知单位会转换，未知单位需用户明确声明。"},
            },
            "required": ["dataset_name"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "sample_value_at_time",
        "description": "查询注册曲线在指定时间的值，默认 linear，也可 nearest；禁止外推。组合曲线必须指定 source。",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_name": {"type": "string", "description": "list_external_datasets 中的注册 alias；不是仓库 CSV 文件名或路径。"},
                "time_column": {"type": "string"},
                "value_column": {"type": "string"},
                "target_time": {"type": "number"},
                "method": {"type": "string", "enum": ["nearest", "linear"]},
                "source": {"type": "string", "description": "组合数据 inspect 返回的 sources 曲线标签。"},
                "time_unit": {"type": "string", "enum": ["ps", "ns", "s", "unknown"], "description": "target_time 采用的单位；对已知原始单位做转换，未知时需明确声明。"},
            },
            "required": ["dataset_name", "target_time"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "summarize_magnetization_curve",
        "description": "总结注册曲线的初值、末值、极值、负到正 crossing 数和首个过零时间，可查询 target_time。",
        "parameters": {
            "type": "object",
            "properties": {
                "dataset_name": {"type": "string", "description": "list_external_datasets 中的注册 alias；不是仓库 CSV 文件名或路径。"},
                "time_column": {"type": "string"},
                "mz_column": {"type": "string"},
                "source": {"type": "string"},
                "target_time": {"type": "number"},
                "time_unit": {"type": "string", "enum": ["ps", "ns", "s", "unknown"]},
            },
            "required": ["dataset_name"],
            "additionalProperties": False,
        },
    },
]

TOOL_FUNCTIONS = {
    "calculator": calculate,
    "electron_energy_from_voltage": electron_energy_from_voltage,
    "list_datasets": list_datasets,
    "inspect_dataset": inspect_dataset,
    "calculate_switching_time": calculate_switching_time,
    "plot_dataset": plot_dataset,
    "list_external_datasets": list_external_datasets,
    "inspect_external_dataset": inspect_external_dataset,
    "compare_switching_times": compare_switching_times,
    "sample_value_at_time": sample_value_at_time,
    "summarize_magnetization_curve": summarize_magnetization_curve,
}


def create_client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请检查项目根目录中的 .env 文件。")

    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"未知工具：{name}")
    return TOOL_FUNCTIONS[name](**arguments)


def run_agent(
    question: str,
    *,
    client: OpenAI | None = None,
    show_steps: bool = True,
) -> str:
    if not question.strip():
        raise ValueError("问题不能为空。")

    api_client = client or create_client()
    conversation: list[Any] = [{"role": "user", "content": question}]

    for _ in range(MAX_STEPS):
        request: dict[str, Any] = {
            "model": MODEL,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": conversation,
            "tools": TOOLS,
        }

        response = api_client.responses.create(**request)
        tool_calls = [item for item in response.output if item.type == "function_call"]

        if not tool_calls:
            if response.output_text:
                return response.output_text
            raise RuntimeError("模型没有返回文本或工具调用。")

        tool_outputs = []
        for tool_call in tool_calls:
            try:
                arguments = json.loads(tool_call.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("工具参数必须是 JSON 对象。")
                result = execute_tool(tool_call.name, arguments)
            except OSError:
                result = {"error": "工具文件操作失败，请检查数据或输出目录的访问权限。"}
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                result = {"error": str(exc)}

            result_text = json.dumps(redact_result(result), ensure_ascii=False)
            if show_steps:
                print(f"[Agent] 调用工具：{tool_call.name}")
                print(f"[Agent] 参数：{tool_call.arguments}")
                print(f"[Tool] 结果：{result_text}")

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": result_text,
                }
            )

        conversation.extend(response.output)
        conversation.extend(tool_outputs)

    return f"Agent 在 {MAX_STEPS} 步内未能完成任务，请尝试简化问题。"
