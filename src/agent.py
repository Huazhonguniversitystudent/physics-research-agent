import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from src.tools.calculator import calculate
from src.tools.physics import electron_energy_from_voltage


MODEL = "deepseek-flash"
MAX_STEPS = 5

SYSTEM_INSTRUCTIONS = (
    "你是面向物理科研学习者的助手。概念解释应直接回答，不要为了补充数值例子而调用工具。"
    "只有用户明确要求数值结果，或不计算就无法完成任务时，才调用合适的工具；"
    "需要计算时不要心算或编造工具结果。"
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
]


def create_client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请检查项目根目录中的 .env 文件。")

    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "calculator":
        return calculate(arguments["expression"])
    if name == "electron_energy_from_voltage":
        return electron_energy_from_voltage(arguments["voltage_v"])
    raise ValueError(f"未知工具：{name}")


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
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                result = {"error": str(exc)}

            result_text = json.dumps(result, ensure_ascii=False)
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
