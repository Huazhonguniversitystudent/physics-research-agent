import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools import data_sources


FIXTURES = Path(__file__).parent / "fixtures"


class DataSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "sources.json"
        patcher = patch.object(data_sources, "CONFIG_FILE", self.config)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.write_registry({"fixture": {"path": str((FIXTURES / "synthetic_external.csv").resolve()), "synthetic": True}})

    def write_registry(self, registry):
        self.config.write_text(json.dumps(registry), encoding="utf-8")

    def test_registry_listing_hides_paths(self):
        result = data_sources.list_external_datasets()
        self.assertEqual(result[0]["name"], "fixture")
        self.assertTrue(result[0]["exists"])
        self.assertNotIn(str(FIXTURES.resolve()), json.dumps(result))

    def test_missing_registry(self):
        self.config.unlink()
        self.assertEqual(data_sources.list_external_datasets(), [])

    def test_invalid_registry(self):
        self.config.write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "注册表"):
            data_sources.list_external_datasets()

    def test_unregistered_name_and_paths(self):
        for name in ("not_registered", "../../secret.csv", "C:/secret.csv", "\\\\server\\share\\x.csv"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                data_sources.load_external_dataset(name)

    def test_inspect_structure(self):
        result = data_sources.inspect_external_dataset("fixture")
        self.assertEqual(result["rows"], 4)
        self.assertEqual(result["columns"], ["Time (ps)", "mumax3_mz", "comsol_mz"])
        self.assertEqual(result["detected_encoding"], "utf-8")
        self.assertEqual(result["detected_delimiter"], ",")
        self.assertEqual(sum(result["missing_values"].values()), 0)

    def test_tab_header_and_scientific_notation(self):
        self.write_registry({"tab": {"path": str((FIXTURES / "synthetic_tab.csv").resolve())}})
        frame, info = data_sources.load_external_dataset("tab")
        self.assertEqual(info["detected_delimiter"], "\t")
        self.assertEqual(frame.columns[0], "Time (s)")
        self.assertEqual(frame.iloc[1, 0], 1e-12)

    def test_bom_and_gbk_semicolon(self):
        for encoding in ("utf-8-sig", "gbk"):
            path = self.root / "encoded.csv"
            path.write_bytes("时间;磁化\n0;-1\n1;1\n".encode(encoding))
            self.write_registry({"encoded": {"path": str(path)}})
            frame, info = data_sources.load_external_dataset("encoded")
            self.assertEqual(frame.columns.tolist(), ["时间", "磁化"])
            self.assertEqual(info["detected_encoding"], encoding)
            self.assertEqual(info["detected_delimiter"], ";")

    def test_malformed_csv(self):
        path = self.root / "bad.csv"
        self.write_registry({"bad": {"path": str(path)}})
        for contents in ("a,b\n1,2,3\n", "", 'a,b\n1,"unterminated\n'):
            path.write_text(contents, encoding="utf-8")
            with self.subTest(contents=contents), self.assertRaises(ValueError):
                data_sources.load_external_dataset("bad")

    def test_non_csv_registration_is_rejected(self):
        self.write_registry({"bad": {"path": str(self.root / "secret.txt")}})
        with self.assertRaises(ValueError):
            data_sources.load_external_dataset("bad")

    def test_registered_symlink_escape_is_rejected(self):
        with patch.object(Path, "resolve", return_value=self.root / "outside.csv"):
            with self.assertRaises(ValueError):
                data_sources.load_external_dataset("fixture")

    def test_preview_and_description_redact_absolute_paths(self):
        path = self.root / "paths.csv"
        path.write_text('time_ps,mz,source\n0,-1,C:\\Users\\private\\real.csv\n1,1,\\\\server\\private\\real.csv\n', encoding="utf-8")
        self.write_registry({"paths": {"path": str(path), "description": "源 C:\\Users\\private\\real.csv"}})
        result = data_sources.inspect_external_dataset("paths")
        text = json.dumps(result)
        self.assertNotIn("private", text)
        self.assertNotIn("private", json.dumps(data_sources.list_external_datasets()))

    def test_missing_file_is_reported_without_path(self):
        self.write_registry({"missing": {"path": str(self.root / "missing.csv")}})
        self.assertFalse(data_sources.list_external_datasets()[0]["exists"])
        with self.assertRaisesRegex(ValueError, "不存在") as caught:
            data_sources.load_external_dataset("missing")
        self.assertNotIn(str(self.root), str(caught.exception))

    def test_composite_only_uses_registered_members(self):
        self.write_registry({"comparison": {"datasets": ["not_registered"]}})
        with self.assertRaises(ValueError):
            data_sources.inspect_external_dataset("comparison")


if __name__ == "__main__":
    unittest.main()
