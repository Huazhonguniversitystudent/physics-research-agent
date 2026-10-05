"""Generate SYNTHETIC demo data; these curves are not simulation results."""

import csv
import math
from pathlib import Path


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "data/examples/synthetic_micromagnetics.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["time_ps", "mumax3_mz", "comsol_mz"])
        for time_ps in range(101):
            writer.writerow([
                time_ps,
                f"{math.tanh((time_ps - 73.8) / 5):.10f}",
                f"{math.tanh((time_ps - 72.6) / 5):.10f}",
            ])
    print("已生成 SYNTHETIC 合成示例数据：data/examples/synthetic_micromagnetics.csv")


if __name__ == "__main__":
    main()
