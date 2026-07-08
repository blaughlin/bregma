"""Validate each fixture's reading against its hand-read ground truth, via both
the manual (hand-tuned crop) path and the auto-locate (loose ROI) front-end."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vernier.pipeline import read_fixture  # noqa: E402

GROUND_TRUTH = json.loads((ROOT / "fixtures" / "ground_truth.json").read_text())
CROPS = json.loads((ROOT / "fixtures" / "crops.json").read_text())

# every fixture reads via auto; those with hand-tuned bands also read via manual
CASES = []
for k in sorted(GROUND_TRUTH):
    CASES.append((k, "auto"))
    if "main_cols" in CROPS.get(k, {}):
        CASES.append((k, "manual"))


@pytest.mark.parametrize("key,mode", CASES)
def test_reading_matches_ground_truth(key, mode):
    truth = GROUND_TRUTH[key]
    result, _ = read_fixture(key, auto=(mode == "auto"))
    err = abs(result["reading_mm"] - truth["value_mm"])
    assert err <= truth["tolerance_mm"], (
        f"{key} [{mode}]: read {result['reading_mm']:.3f} mm vs truth "
        f"{truth['value_mm']} mm (error {err:.3f} mm > {truth['tolerance_mm']})"
    )
