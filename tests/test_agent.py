import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.agent import MAX_STEPS, TOOL_FUNCTIONS, TOOLS, run_agent


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(type="function_call", name=name, arguments=json.dumps(arguments), call_id=call_id)


def response(*calls, text=""):
    return SimpleNamespace(output=list(calls), output_text=text)


class AgentLoopTests(unittest.TestCase):
    def test_rag_fake_citation_is_rejected(self):
        client = Mock()
        client.responses.create.side_effect = [response(tool_call("search_knowledge_base", {"query": "Tool Calling"})), response(text="答案[docs/fake.md:L1-L2]")]
        with patch("src.agent.execute_tool", return_value={"results": [{"citation": "[docs/a.md:L1-L2]"}]}):
            self.assertIn("引用校验未通过", run_agent("给出处", client=client, show_steps=False))

    def test_rag_without_evidence_cannot_use_model_knowledge(self):
        client = Mock()
        client.responses.create.side_effect = [response(tool_call("search_knowledge_base", {"query": "量子霍尔"})), response(text="擅自回答")]
        with patch("src.agent.execute_tool", return_value={"found": False, "results": []}):
            self.assertIn("没有足够证据", run_agent("根据文档", client=client, show_steps=False))

    def test_rag_valid_citation_is_accepted(self):
        client = Mock()
        answer = "Python 执行工具。[docs/a.md:L1-L2]"
        client.responses.create.side_effect = [response(tool_call("search_knowledge_base", {"query": "执行 Python"})), response(text=answer)]
        with patch("src.agent.execute_tool", return_value={"results": [{"citation": "[docs/a.md:L1-L2]"}]}):
            self.assertEqual(run_agent("给出处", client=client, show_steps=False), answer)

    def test_registered_tool_schemas_match_dispatch(self):
        self.assertEqual({tool["name"] for tool in TOOLS}, set(TOOL_FUNCTIONS))
        for tool in TOOLS:
            parameters = tool["parameters"]
            self.assertEqual(parameters["type"], "object")
            self.assertTrue(set(parameters.get("required", [])).issubset(parameters["properties"]))

    def test_private_paths_are_redacted_before_model_feedback(self):
        client = Mock()
        client.responses.create.side_effect = [response(tool_call("list_external_datasets", {})), response(text="完成")]
        with patch("src.agent.execute_tool", return_value={"note": "C:/Users/private/data.csv"}):
            run_agent("列出数据", client=client, show_steps=False)
        output = client.responses.create.call_args.kwargs["input"][-1]["output"]
        self.assertNotIn("C:/Users", output)
        self.assertIn("隐藏", output)

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
