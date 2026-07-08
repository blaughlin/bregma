"""Validate each fixture's reading against its hand-read ground truth."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vernier.pipeline import read_fixture  # noqa: E402

GROUND_TRUTH = json.loads((ROOT / "fixtures" / "ground_truth.json").read_text())


@pytest.mark.parametrize("key", sorted(GROUND_TRUTH))
def test_reading_matches_ground_truth(key):
    truth = GROUND_TRUTH[key]
    result, _ = read_fixture(key)
    err = abs(result["reading_mm"] - truth["value_mm"])
    assert err <= truth["tolerance_mm"], (
        f"{key}: read {result['reading_mm']:.3f} mm vs truth "
        f"{truth['value_mm']} mm (error {err:.3f} mm > {truth['tolerance_mm']})"
    )
