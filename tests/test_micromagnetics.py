import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.tools import data_sources, micromagnetics, scientific_data


FIXTURES = Path(__file__).parent / "fixtures"


class MicromagneticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "sources.json"
        self.config.write_text(json.dumps({
            "wide": {"path": str((FIXTURES / "synthetic_external.csv").resolve()), "synthetic": True},
            "single": {"path": str((FIXTURES / "synthetic_tab.csv").resolve()), "label": "single", "synthetic": True},
            "comparison": {"datasets": ["single", "single_two"], "synthetic": True},
            "single_two": {"path": str((FIXTURES / "synthetic_tab.csv").resolve()), "label": "second", "synthetic": True},
        }), encoding="utf-8")
        patcher = patch.object(data_sources, "CONFIG_FILE", self.config)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_column_detection(self):
        result = micromagnetics.detect_micromagnetic_columns(pd.DataFrame(columns=["Time (ps)", "mumax3_mz", "comsol_mz"]))
        self.assertEqual(result["time_column"], "Time (ps)")
        self.assertEqual(result["mz_columns"], ["mumax3_mz", "comsol_mz"])

    def test_normalized_column_detection(self):
        result = micromagnetics.detect_micromagnetic_columns(pd.DataFrame(columns=[" TIME_PS ", "< M_z >"]))
        self.assertEqual(result["time_column"], " TIME_PS ")
        self.assertEqual(result["mz_columns"], ["< M_z >"])

    def test_ambiguous_columns_require_explicit_selection(self):
        with self.assertRaisesRegex(ValueError, "指定"):
            micromagnetics.detect_micromagnetic_columns(pd.DataFrame(columns=["time_ps", "Time (s)", "mz"]))

    def test_unknown_columns_require_explicit_selection(self):
        with self.assertRaisesRegex(ValueError, "指定"):
            micromagnetics.detect_micromagnetic_columns(pd.DataFrame(columns=["step", "value"]))

    def test_units(self):
        for column, expected in (("time_ps", "ps"), ("Time (ns)", "ns"), ("time_s", "s"), ("Time (s)", "s"), ("t", "unknown")):
            with self.subTest(column=column):
                self.assertEqual(micromagnetics.detect_time_unit(column), expected)

    def test_compare_and_interpolation(self):
        result = micromagnetics.compare_switching_times("wide")
        self.assertEqual(result["results"][0]["switching_time"], 1.5)
        self.assertEqual(result["results"][1]["switching_time"], 1.0)
        self.assertEqual(result["earlier"], "comsol_mz")
        self.assertEqual(result["difference"], 0.5)
        self.assertEqual(result["time_unit"], "ps")

    def test_nearest_and_linear_sampling(self):
        linear = micromagnetics.sample_value_at_time("wide", "Time (ps)", "mumax3_mz", 1.25)
        nearest = micromagnetics.sample_value_at_time("wide", "Time (ps)", "mumax3_mz", 1.25, "nearest")
        self.assertAlmostEqual(linear["value"], -0.1)
        self.assertEqual(nearest["value"], -0.2)
        self.assertEqual(nearest["sample_time"], 1.0)

    def test_exact_sample_and_out_of_range(self):
        self.assertEqual(micromagnetics.sample_value_at_time("wide", "Time (ps)", "mumax3_mz", 2)["value"], 0.2)
        with self.assertRaisesRegex(ValueError, "范围"):
            micromagnetics.sample_value_at_time("wide", "Time (ps)", "mumax3_mz", 100)

    def test_summary(self):
        result = micromagnetics.summarize_magnetization_curve("wide", "Time (ps)", "mumax3_mz", target_time=2)
        self.assertEqual(result["initial_mz"], -1)
        self.assertEqual(result["final_mz"], 1)
        self.assertEqual(result["crossing_count"], 1)
        self.assertEqual(result["first_switching_time"], 1.5)
        self.assertEqual(result["target_time_value"]["value"], 0.2)

    def test_no_crossing_summary_and_compare(self):
        path = self.root / "no.csv"
        path.write_text("time_ps,mz\n0,-1\n1,-0.5\n", encoding="utf-8")
        self.config.write_text(json.dumps({"no": {"path": str(path)}}), encoding="utf-8")
        result = micromagnetics.summarize_magnetization_curve("no")
        self.assertIsNone(result["first_switching_time"])
        self.assertEqual(result["crossing_count"], 0)
        with self.assertRaises(ValueError):
            micromagnetics.compare_switching_times("no")

    def test_composite_retains_original_sampling_and_units(self):
        frame, info = micromagnetics.load_normalized_dataset("comparison")
        self.assertEqual(frame.columns.tolist(), ["time", "mz", "source"])
        self.assertEqual(len(frame), 8)
        self.assertEqual(set(frame["source"]), {"single", "second"})
        self.assertEqual(info["time_unit"], "s")
        result = micromagnetics.compare_switching_times("comparison")
        self.assertEqual(result["difference"], 0)
        self.assertEqual(result["earlier"], "tie")
        self.assertAlmostEqual(result["results"][0]["switching_time"], 1.5e-12, delta=1e-25)

    def test_composite_sampling_requires_source(self):
        with self.assertRaisesRegex(ValueError, "source"):
            micromagnetics.sample_value_at_time("comparison", "time", "mz", 1.5e-12)
        result = micromagnetics.sample_value_at_time("comparison", "time", "mz", 1.5e-12, source="single")
        self.assertAlmostEqual(result["value"], 0, delta=1e-15)

    def test_unit_override_and_conversion(self):
        result = micromagnetics.sample_value_at_time("single", "Time (s)", "avg_mz", 1.5, time_unit="ps")
        self.assertEqual(result["time_unit"], "ps")
        self.assertAlmostEqual(result["value"], 0, delta=1e-15)

    def test_external_plot_and_path_safety(self):
        with patch.object(scientific_data, "PLOTS_DIR", self.root / "plots"):
            result = scientific_data.plot_dataset("comparison", "time", ["mz"], "external_test.png")
            self.assertGreater((self.root / "plots/external_test.png").stat().st_size, 0)
            self.assertNotIn(str(FIXTURES.resolve()), json.dumps(result))
            with self.assertRaises(ValueError):
                scientific_data.plot_dataset("comparison", "time", ["mz"], "../../unsafe.png")


if __name__ == "__main__":
    unittest.main()
