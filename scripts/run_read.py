"""Run the full pipeline on a fixture: print the reading, dump debug PNGs.

Usage:  python scripts/run_read.py [image3 ...]
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vernier import debug           # noqa: E402
from vernier.pipeline import read_fixture, ROOT as PKG_ROOT  # noqa: E402


def run(key, save_debug=True):
    result, im = read_fixture(key, verbose=True)
    if save_debug:
        out_dir = PKG_ROOT / "debug"
        out_dir.mkdir(exist_ok=True)
        out = out_dir / f"{key}.png"
        debug.render(out, im["gray"], im["main_rows"], im["vern_rows"],
                     im["main_cols"], im["vern_cols"],
                     im["main_prof"], im["main_ticks"],
                     im["vern_prof"], im["vern_ticks"],
                     result["fine"], result)
        print(f"[{key}] debug -> {out}")
    return result


if __name__ == "__main__":
    for k in (sys.argv[1:] or ["image3"]):
        run(k)
