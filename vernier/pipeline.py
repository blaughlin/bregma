"""End-to-end pipeline: fixture config -> mm reading (+ intermediates).

Shared by the CLI (scripts/run_read.py) and the test suite so they exercise the
exact same code path.
"""
import json
from pathlib import Path

import numpy as np

from vernier import imaging, profile, ticks, read

ROOT = Path(__file__).resolve().parents[1]


def read_fixture(key, root=ROOT, verbose=False):
    """Run steps 1-5 on a named fixture. Returns (result, intermediates)."""
    cfg = json.loads((root / "fixtures" / "crops.json").read_text())[key]

    gray = imaging.load_gray(root / cfg["path"], downscale=cfg.get("downscale", 1))
    angle = cfg["deskew_deg"]
    if angle is None:
        angle = imaging.estimate_skew(gray, rows=tuple(cfg["rows"]))
    gray = imaging.deskew(gray, angle)

    main_rows = tuple(cfg["rows"])
    vern_rows = tuple(cfg.get("vernier_rows", cfg["rows"]))
    main_prof = profile.band_profile(imaging.extract_band(gray, main_rows, tuple(cfg["main_cols"])))
    vern_prof = profile.band_profile(imaging.extract_band(gray, vern_rows, tuple(cfg["vernier_cols"])))

    main_ticks, _ = ticks.find_ticks(main_prof, min_distance=cfg["main_min_dist"],
                                     prominence=cfg.get("main_prominence", 0.03))
    vern_ticks, _ = ticks.find_ticks(vern_prof, min_distance=cfg["vernier_min_dist"],
                                     prominence=cfg.get("vernier_prominence", 0.03))
    main_abs = main_ticks + main_rows[0]
    vern_abs = vern_ticks + vern_rows[0]

    result = read.read_scale(
        main_abs, vern_abs,
        anchor=cfg["anchor"],
        vernier_zero_row=cfg.get("vernier_zero_row"),
        mm_per_div=cfg.get("mm_per_div", 1.0),
        vernier_ref=cfg.get("vernier_ref", "bottom"),
    )

    if verbose:
        print(f"[{key}] main {len(main_abs)} ticks pitch~"
              f"{np.median(np.diff(np.sort(main_abs))):.2f}px | "
              f"vernier {len(vern_abs)} ticks pitch~"
              f"{np.median(np.diff(np.sort(vern_abs))):.2f}px")
        print(f"[{key}] READING = {result['reading_mm']:.3f} mm "
              f"(coarse {result['coarse_mm']:.2f} + fine {result['fine_mm']:.3f}, "
              f"n*={result['fine']['n_star']:.2f}, rms={result['fine']['resid_rms']:.2f}px)")

    intermediates = dict(
        gray=gray, main_rows=main_rows, vern_rows=vern_rows,
        main_cols=tuple(cfg["main_cols"]), vern_cols=tuple(cfg["vernier_cols"]),
        main_prof=main_prof, main_ticks=main_ticks,
        vern_prof=vern_prof, vern_ticks=vern_ticks,
    )
    return result, intermediates
