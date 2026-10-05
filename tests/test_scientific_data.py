import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools import scientific_data


DATASET = "synthetic_micromagnetics.csv"


class SyntheticDataTests(unittest.TestCase):
    def test_list_datasets(self):
        datasets = scientific_data.list_datasets()
        example = next(item for item in datasets if item["dataset"] == DATASET)
        self.assertTrue(example["synthetic"])
        self.assertEqual(example["path"], f"data/examples/{DATASET}")
        self.assertGreater(example["size_bytes"], 0)

    def test_inspect_dataset(self):
        result = scientific_data.inspect_dataset(DATASET)
        self.assertEqual(result["rows"], 101)
        self.assertEqual(result["columns"], ["time_ps", "mumax3_mz", "comsol_mz"])
        self.assertEqual(result["column_count"], 3)
        self.assertEqual(len(result["preview"]), 5)
        self.assertEqual(sum(result["missing_values"].values()), 0)

    def test_mumax3_switching_time(self):
        result = scientific_data.calculate_switching_time(DATASET, "time_ps", "mumax3_mz")
        self.assertAlmostEqual(result["switching_time"], 73.8, delta=0.005)
        self.assertEqual(result["time_unit"], "ps")
        self.assertFalse(result["sorted"])
        self.assertEqual(result["sorting_note"], "输入时间已递增，无需重新排序。")

    def test_comsol_switching_time(self):
        result = scientific_data.calculate_switching_time(DATASET, "time_ps", "comsol_mz")
        self.assertAlmostEqual(result["switching_time"], 72.6, delta=0.005)


class ScientificDataEdgeTests(unittest.TestCase):
    def setUp(self):
        # Fixtures and PNGs live only in a disposable test directory.
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "examples").mkdir()
        (self.root / "local").mkdir()
        self.plots = self.root / "plots"
        self.patch_data = patch.object(scientific_data, "DATA_ROOT", self.root)
        self.patch_plots = patch.object(scientific_data, "PLOTS_DIR", self.plots)
        self.patch_data.start()
        self.patch_plots.start()
        self.addCleanup(self.patch_data.stop)
        self.addCleanup(self.patch_plots.stop)

    def write_csv(self, rows, header="time_ps,mz", name="crossing.csv", source="local"):
        path = self.root / source / name
        path.write_text(header + "\n" + rows, encoding="utf-8")
        return f"{source}/{name}"

    def test_linear_interpolation(self):
        dataset = self.write_csv("0,-1\n1,-0.2\n2,0.2\n")
        result = scientific_data.calculate_switching_time(dataset, "time_ps", "mz")
        self.assertEqual(result["switching_time"], 1.5)
        self.assertEqual(result["bracket"], {"t1": 1.0, "mz1": -0.2, "t2": 2.0, "mz2": 0.2})
        self.assertFalse(result["synthetic"])

    def test_first_crossing_is_used(self):
        dataset = self.write_csv("0,-1\n1,1\n2,-1\n3,1\n")
        self.assertEqual(scientific_data.calculate_switching_time(dataset, "time_ps", "mz")["switching_time"], 0.5)

    def test_exact_zero_after_negative(self):
        dataset = self.write_csv("0,-1\n1,0\n2,1\n")
        self.assertEqual(scientific_data.calculate_switching_time(dataset, "time_ps", "mz")["switching_time"], 1.0)

    def test_initial_zero_does_not_prove_negative_to_positive_crossing(self):
        dataset = self.write_csv("0,0\n1,1\n")
        with self.assertRaisesRegex(ValueError, "未找到"):
            scientific_data.calculate_switching_time(dataset, "time_ps", "mz")

    def test_no_crossing(self):
        dataset = self.write_csv("0,-1\n1,-0.5\n2,-0.1\n")
        with self.assertRaisesRegex(ValueError, "未找到"):
            scientific_data.calculate_switching_time(dataset, "time_ps", "mz")

    def test_invalid_numeric_data(self):
        for rows in ("0,-1\n1,hello\n", "0,-1\n1,\n", "0,-1\n1,inf\n"):
            with self.subTest(rows=rows):
                dataset = self.write_csv(rows)
                with self.assertRaises(ValueError):
                    scientific_data.calculate_switching_time(dataset, "time_ps", "mz")

    def test_missing_column(self):
        dataset = self.write_csv("0,-1\n1,1\n")
        with self.assertRaisesRegex(ValueError, "列不存在"):
            scientific_data.calculate_switching_time(dataset, "time_ps", "unknown")

    def test_too_few_rows(self):
        dataset = self.write_csv("0,-1\n")
        with self.assertRaisesRegex(ValueError, "至少两行"):
            scientific_data.calculate_switching_time(dataset, "time_ps", "mz")

    def test_unsorted_time_and_arbitrary_columns(self):
        dataset = self.write_csv("2,0.2\n0,-1\n1,-0.2\n", header="Time,m_z")
        result = scientific_data.calculate_switching_time(dataset, "Time", "m_z")
        self.assertEqual(result["switching_time"], 1.5)
        self.assertTrue(result["sorted"])
        self.assertEqual(result["time_unit"], "unknown")

    def test_duplicate_time_is_rejected(self):
        dataset = self.write_csv("0,-1\n0,1\n")
        with self.assertRaisesRegex(ValueError, "重复"):
            scientific_data.calculate_switching_time(dataset, "time_ps", "mz")

    def test_reverse_direction_and_ns(self):
        dataset = self.write_csv("0,1\n1,-1\n", header="time_ns,mz")
        result = scientific_data.calculate_switching_time(dataset, "time_ns", "mz", "positive_to_negative")
        self.assertEqual(result["switching_time"], 0.5)
        self.assertEqual(result["time_unit"], "ns")

    def test_invalid_direction(self):
        dataset = self.write_csv("0,-1\n1,1\n")
        with self.assertRaises(ValueError):
            scientific_data.calculate_switching_time(dataset, "time_ps", "mz", "any")

    def test_missing_file(self):
        with self.assertRaisesRegex(ValueError, "不存在"):
            scientific_data.inspect_dataset("missing.csv")

    def test_unsafe_paths(self):
        for dataset in ("../../secret.csv", "../../../secret.csv", "local/../examples/x.csv", "C:\\secret.csv", "C:/secret.csv", "\\\\server\\share\\x.csv", "/tmp/secret.csv"):
            with self.subTest(dataset=dataset), self.assertRaises(ValueError):
                scientific_data.inspect_dataset(dataset)

    def test_ambiguous_filename(self):
        self.write_csv("0,-1\n1,1\n", source="local")
        self.write_csv("0,-1\n1,1\n", source="examples")
        with self.assertRaisesRegex(ValueError, "同名"):
            scientific_data.inspect_dataset("crossing.csv")

    def test_resolved_path_escape(self):
        self.write_csv("0,-1\n1,1\n")
        # Model a symlink whose final target is outside an allowed directory.
        with patch.object(Path, "resolve", return_value=self.root / "secret.csv"):
            with self.assertRaisesRegex(ValueError, "允许目录"):
                scientific_data.inspect_dataset("local/crossing.csv")

    def test_missing_preview_values_are_json_null(self):
        dataset = self.write_csv("0,-1\n1,\n")
        result = scientific_data.inspect_dataset(dataset)
        self.assertIsNone(result["preview"][1]["mz"])
        self.assertEqual(result["missing_values"]["mz"], 1)

    def test_plot_exists_and_is_closed(self):
        dataset = self.write_csv("0,-1\n1,1\n")
        result = scientific_data.plot_dataset(dataset, "time_ps", ["mz"], "test_plot")
        output = self.plots / "test_plot.png"
        self.assertTrue(output.is_file())
        self.assertGreater(output.stat().st_size, 0)
        self.assertEqual(result["path"], "outputs/plots/test_plot.png")
        from matplotlib import pyplot as plt
        self.assertEqual(plt.get_fignums(), [])

    def test_unsafe_plot_names(self):
        dataset = self.write_csv("0,-1\n1,1\n")
        for name in ("../../abc.png", "C:/abc.png", "\\\\server\\abc.png", "../abc"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                scientific_data.plot_dataset(dataset, "time_ps", ["mz"], name)


if __name__ == "__main__":
    unittest.main()
