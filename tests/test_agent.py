import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

from src.agent import MAX_STEPS, run_agent


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(type="function_call", name=name, arguments=json.dumps(arguments), call_id=call_id)


def response(*calls, text=""):
    return SimpleNamespace(output=list(calls), output_text=text)


class AgentLoopTests(unittest.TestCase):
    def test_direct_answer(self):
        client = Mock()
        client.responses.create.return_value = response(text="瑞利散射")
        self.assertEqual(run_agent("天为什么是蓝色的？", client=client, show_steps=False), "瑞利散射")
        self.assertEqual(client.responses.create.call_count, 1)

    def test_multiple_tool_calls_and_result_feedback(self):
        requests = []
        replies = iter([
            response(tool_call("calculator", {"expression": "2+3"}, "first"), tool_call("electron_energy_from_voltage", {"voltage_v": 5}, "second")),
            response(tool_call("calculator", {"expression": "5*2"}, "third")),
            response(text="完成"),
        ])

        def create(**request):
            requests.append(deepcopy(request))
            return next(replies)

        client = Mock()
        client.responses.create.side_effect = create
        self.assertEqual(run_agent("连续调用工具", client=client, show_steps=False), "完成")
        outputs = [item for item in requests[1]["input"] if isinstance(item, dict) and item.get("type") == "function_call_output"]
        self.assertEqual([item["call_id"] for item in outputs], ["first", "second"])
        self.assertEqual(json.loads(outputs[0]["output"]), 5)
        self.assertEqual(json.loads(outputs[1]["output"])["energy_ev"], 5)
        self.assertEqual(len(requests), 3)

    def test_step_limit(self):
        client = Mock()
        client.responses.create.return_value = response(tool_call("calculator", {"expression": "1+1"}))
        self.assertIn("5 步", run_agent("重复", client=client, show_steps=False))
        self.assertEqual(client.responses.create.call_count, MAX_STEPS)

    def test_tool_error_is_returned_to_model(self):
        requests = []
        replies = iter([response(tool_call("inspect_dataset", {"dataset": "../../secret.csv"})), response(text="拒绝非法路径")])

        def create(**request):
            requests.append(deepcopy(request))
            return next(replies)

        client = Mock()
        client.responses.create.side_effect = create
        self.assertEqual(run_agent("读取", client=client, show_steps=False), "拒绝非法路径")
        self.assertIn("error", json.loads(requests[1]["input"][-1]["output"]))


if __name__ == "__main__":
    unittest.main()
