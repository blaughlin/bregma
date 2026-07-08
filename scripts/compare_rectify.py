"""Measure the effect of the homography perspective rectification.

Reads every ground-truth fixture via the auto path with rectification OFF and
ON, and prints the error against the hand-read value. Documents the finding that
global rectification does not help (and usually hurts) this vernier reader.

    python scripts/compare_rectify.py
"""
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

from vernier.pipeline import read_fixture  # noqa: E402

GT = json.loads((ROOT / "fixtures" / "ground_truth.json").read_text())

print(f"{'fixture':8}  {'truth':>7}  {'off':>8} {'err':>6}  {'on':>8} {'err':>6}   verdict")
for key in sorted(GT):
    truth = GT[key]["value_mm"]
    off, _ = read_fixture(key, auto=True, rectify_override=False)
    on, _ = read_fixture(key, auto=True, rectify_override=True)
    e_off = abs(off["reading_mm"] - truth)
    e_on = abs(on["reading_mm"] - truth)
    verdict = "rectify better" if e_on < e_off - 1e-6 else "rectify worse/equal"
    print(f"{key:8}  {truth:7.1f}  {off['reading_mm']:8.3f} {e_off:6.3f}  "
          f"{on['reading_mm']:8.3f} {e_on:6.3f}   {verdict}")
