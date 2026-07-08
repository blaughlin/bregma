# Bregma - Stereotax Vernier Reader (Stage 1 prototype)

Reads a Kopf-style stereotaxic **vernier scale** from a still photo and reports the
coordinate in mm. This repo is **Stage 1**: a Python still-image prototype that proves the
reading algorithm against hand-read ground truth before any iOS work. See `CLAUDE.md` for
the full design and the two-stage plan.

**Not a diagnostic device - always verify against the physical scale.**

## Status
Vertical scale (Kopf 957), three hand-read positions across three very different captures,
all inside the 0.1 mm (one-vernier-division) gate:

| fixture | reads | hand-read | error | notes |
|---------|-------|-----------|-------|-------|
| `image3` | 40.421 mm | 40.4 mm | 0.021 mm | native resolution, fit RMS 0.53 px |
| `image2` | 16.077 mm | 16.1 mm | 0.023 mm | 3024x4032 + perforated background, `downscale=3`, fit RMS 0.15 px |
| `image1` | 63.759 mm | 63.8 mm | 0.041 mm | 640x480 low-res wide shot (EXIF-rotated), `upscale=3`, fit RMS 0.46 px |

## How it works (steps 1-5, per CLAUDE.md)
1. **`imaging.py`** - load (optional downscale), deskew (small rotation that maximises
   tick-profile contrast), and slice the main-scale and vernier tick columns into bands.
2. **`profile.py`** - collapse each band across its width to a 1-D intensity profile
   (dark ticks = dips); glare is masked and interpolated.
3. **`ticks.py`** - detect dips (`scipy.signal.find_peaks`) and refine each to sub-pixel with
   a parabolic vertex.
4. **`read.py`** - fit both scales to regular grids (`fit_grid`, with outlier rejection, which
   repairs missed/mis-located ticks); the main pitch is measured *locally* to survive the
   perspective gradient. **Fine reading** = global line fit of each vernier tick's offset to
   the main grid vs. its number, whose zero crossing is the aligned vernier number `n*`
   (fine = `n* x 0.1 mm`). **Coarse reading** = the main division the vernier zero sits past,
   anchored to a known value (OCR's job in the app).
5. Combine coarse + fine.

`debug.py` renders the deskewed crop with band boxes, both profiles with detected ticks, and
the step-4 fit - the primary debugging surface (see `debug/*.png`).

## Setup
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows; use bin/ on *nix
```

## Run
```bash
.venv/Scripts/python scripts/run_read.py image3 image2   # prints readings, writes debug PNGs
.venv/Scripts/python -m pytest tests/                    # validate against ground truth
```

## Fixtures
- `SampleImages/` - source photos.
- `fixtures/crops.json` - per-image downscale, deskew angle, band columns/rows, detection
  params, and the numbered-mark anchor.
- `fixtures/ground_truth.json` - hand-read true value + tolerance per image.

## Not yet done
- Auto skew estimate is fooled by strong periodic backgrounds (e.g. image2's perforated
  panel, image1's carpet); currently the angle is set per-fixture. Restrict the estimate to
  the scale columns once the scale is auto-located.
- Rectification front-end (auto-detect + perspective-warp the scale) - deferred until the read
  is trusted on more frames.
- OCR cross-check of the printed numbers (the coarse integer is anchored manually for now).
- The iOS app (Stage 2).
