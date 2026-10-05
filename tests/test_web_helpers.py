import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fixtures.generate_sample_pdf import generate_sample_pdf
from src.agent import execute_tool, run_agent
from src.rag.documents import load_documents
from src.rag.pdf_documents import list_knowledge_papers
from src.web.public_mode import (
    PUBLIC_TOOL_NAMES,
    is_public_demo_mode,
    public_tool_schemas,
    sanitize_trace,
    synthetic_demo,
)


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(type="function_call", name=name, arguments=json.dumps(arguments), call_id=call_id)


def response(*calls, text=""):
    return SimpleNamespace(output=list(calls), output_text=text)


class PublicModeTests(unittest.TestCase):
    def test_public_mode_defaults_true(self):
        self.assertTrue(is_public_demo_mode({}))
        self.assertTrue(is_public_demo_mode({"PHYSICS_AGENT_PUBLIC_DEMO": "1"}))
        self.assertFalse(is_public_demo_mode({"PHYSICS_AGENT_PUBLIC_DEMO": "0"}))

    def test_private_tools_are_absent_and_rejected(self):
        schemas = public_tool_schemas([
            {"name": "calculator"}, {"name": "list_external_datasets"}, {"name": "compare_switching_times"}
        ])
        self.assertEqual([tool["name"] for tool in schemas], ["calculator"])
        self.assertNotIn("list_external_datasets", PUBLIC_TOOL_NAMES)
        with self.assertRaises(ValueError):
            execute_tool("list_external_datasets", {}, public_mode=True)

    def test_public_dataset_is_only_synthetic(self):
        rows = execute_tool("list_datasets", {}, public_mode=True)
        self.assertTrue(rows)
        self.assertTrue(all(row["synthetic"] and row["path"].startswith("data/examples/") for row in rows))
        with self.assertRaises(ValueError):
            execute_tool("inspect_dataset", {"dataset": "local/private.csv"}, public_mode=True)

        inspected = execute_tool("inspect_dataset", {"dataset": "synthetic_micromagnetics.csv"}, public_mode=True)
        self.assertEqual(inspected["path"], "data/examples/synthetic_micromagnetics.csv")

    def test_synthetic_demo_is_available(self):
        result = synthetic_demo()
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["dataset"], "synthetic_micromagnetics.csv")
        self.assertGreater(result["difference_ps"], 0)
        self.assertTrue((Path(__file__).parents[1] / result["plot_path"]).is_file())

    def test_public_documents_and_papers_exclude_local(self):
        temp_root = Path(__file__).parents[1] / "outputs"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as directory:
            root = Path(directory)
            for name in ("docs", "knowledge/public/papers", "knowledge/local/papers"):
                (root / name).mkdir(parents=True)
            (root / "docs/public.md").write_text("public", encoding="utf-8")
            (root / "docs/Resume_Project_Description.md").write_text("portfolio only", encoding="utf-8")
            (root / "knowledge/local/private.md").write_text("PRIVATE_SENTINEL", encoding="utf-8")
            generate_sample_pdf(root / "knowledge/public/papers/public.pdf")
            generate_sample_pdf(root / "knowledge/local/papers/private.pdf")
            documents = load_documents(root, include_local=False)
            papers = list_knowledge_papers(root, include_local=False)
            self.assertEqual([item["source"] for item in documents], ["docs/public.md"])
            self.assertEqual([item["paper_id"] for item in papers], ["public"])

    def test_trace_is_sanitized_and_does_not_contain_api_key_or_private_path(self):
        secret = "private-test-secret-value"
        trace = sanitize_trace([{ "tool": "inspect_dataset", "arguments": {"api_key": secret},
                                  "result": {"path": "C:/Users/private/secret.csv", "preview": "x" * 1000},
                                  "citations": []}])
        payload = json.dumps(trace, ensure_ascii=False)
        self.assertNotIn(secret, payload)
        self.assertNotIn("C:/Users", payload)
        self.assertIn("隐藏", payload)
        self.assertLess(len(payload), 900)

    def test_collect_trace_keeps_old_return_type_by_default(self):
        client = Mock()
        client.responses.create.side_effect = [response(tool_call("calculator", {"expression": "2+3"})), response(text="结果是 5")]
        result = run_agent("2+3", client=client, show_steps=False, public_mode=True, collect_trace=True)
        self.assertEqual(result["answer"], "结果是 5")
        self.assertEqual(result["trace"][0]["tool"], "calculator")
        self.assertEqual(result["trace"][0]["arguments"], {"expression": "2+3"})

        client = Mock()
        client.responses.create.return_value = response(text="普通回答")
        self.assertEqual(run_agent("你好", client=client, show_steps=False), "普通回答")

    def test_api_key_is_never_added_to_trace(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-do-not-show"}):
            client = Mock()
            client.responses.create.side_effect = [response(tool_call("calculator", {"expression": "1+1"})), response(text="2")]
            result = run_agent("1+1", client=client, show_steps=False, public_mode=True, collect_trace=True)
        self.assertNotIn("sk-do-not-show", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
