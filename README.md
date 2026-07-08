# Bregma - Stereotax Vernier Reader (Stage 1 prototype)

Reads a Kopf-style stereotaxic **vernier scale** from a still photo and reports the
coordinate in mm. This repo is **Stage 1**: a Python still-image prototype that proves the
reading algorithm against hand-read ground truth before any iOS work. See `CLAUDE.md` for
the full design and the two-stage plan.

**Not a diagnostic device - always verify against the physical scale.**

## Status
Vertical scale (Kopf 957), four hand-read positions across very different captures, all read
(from just a loose ROI) inside the 0.1 mm (one-vernier-division) gate:

| fixture | hand-read | reading | error | notes |
|---------|-----------|---------|-------|-------|
| `image3` | 40.4 mm | 40.381 mm | 0.019 mm | native resolution |
| `image2` | 16.1 mm | 16.101 mm | 0.001 mm | 3024x4032 + perforated background, `downscale=3` |
| `image1` | 63.8 mm | 63.856 mm | 0.056 mm | 640x480 low-res wide shot (EXIF-rotated), `upscale=3` |
| `image4` | 63.6 mm | 63.587 mm | 0.013 mm | 640x480 low-res wide shot, `upscale=3` |

## Front-end: auto-location (`locate.py`)
Given a **loose ROI** around the scale (what the app's framing quality-gate will provide), the
front-end replaces the hand-tuned crop:
- Scores every column by how *periodic* its vertical profile is (autocorrelation peak) - tick
  columns light up; smooth metal, printed numbers, and background do not.
- Estimates deskew *iteratively*: detect bands, measure the residual tilt of the full-height
  main band (rotate a narrow crop of it, maximise row-profile variance), accumulate, repeat.
  This converges from any starting tilt and, confined to the ROI, is immune to the periodic
  backgrounds (image2's perforated panel, image1's carpet) that fool a whole-frame estimate.
- Separates the **main** band (ticks span the full height) from the **vernier** band (ticks
  only in the cursor sub-region) by per-column *row coverage*, since the two bands abut and
  can't be split by a column gap. Yields the vernier row range and tick pitch too.

Run it with `--auto`; the read then needs only the ROI, scale factor, `mm_per_div`, vernier
reference end, and the coarse integer anchor.

## Perspective rectification (`rectify.py`) — evaluated, off by default
A homography built from the tick grid (send every main-tick line to a horizontal, equally-
spaced target; apply it to the sub-pixel tick *coordinates*, not the pixels, to preserve
precision) removes residual keystone and foreshortening after deskew. **Measured across all
four fixtures it does not help** — it improves one and slightly degrades the other three:

```
fixture  truth   rectify off   rectify on
image1   63.8    err 0.056     err 0.095
image2   16.1    err 0.001     err 0.016
image3   40.4    err 0.019     err 0.011
image4   63.6    err 0.013     err 0.028
```
(reproduce with `python scripts/compare_rectify.py`.) The reason: the fine read is a *local*
comparison (a vernier tick against its adjacent main ticks), and `read.py` already measures
the main pitch locally where the vernier sits — so a global warp can't improve the local
alignment and only injects its own fit error. Kept available (`"rectify": true` per fixture)
but disabled by default. **Takeaway for the iOS port: skip perspective warp.**

## How it works (steps 1-5, per CLAUDE.md)
1. **`imaging.py`** - load (optional up/downscale, EXIF-aware), deskew, and slice the
   main-scale and vernier tick columns into bands.
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
.venv/Scripts/python scripts/run_read.py image3 image2 image1 image4   # read + debug PNGs
.venv/Scripts/python -m pytest tests/                    # validate vs ground truth
.venv/Scripts/python scripts/compare_rectify.py          # perspective-rectify off vs on
```

## Fixtures
- `SampleImages/` - source photos.
- `fixtures/crops.json` - per-image scale factor, loose `roi`, and the coarse anchor value.
  Everything else (deskew, bands, tick pitch) is auto-detected. A hand-tuned crop can still be
  supplied instead (set `"auto": false` with explicit `deskew_deg`/`main_cols`/... fields).
- `fixtures/ground_truth.json` - hand-read true value + tolerance per image.

## Not yet done
- **Auto ROI**: the loose ROI is still supplied per fixture (the app gets it from the framing
  quality-gate / Vision rectangle detection); full-frame scale detection is out of scope here.
- Perspective rectification was implemented and evaluated (see above); not pursued further.
- OCR cross-check of the printed numbers (the coarse integer is anchored manually for now).
- The iOS app (Stage 2).
