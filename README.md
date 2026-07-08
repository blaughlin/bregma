# Bregma - Stereotax Vernier Reader (Stage 1 prototype)

Reads a Kopf-style stereotaxic **vernier scale** from a still photo and reports the
coordinate in mm. This repo is **Stage 1**: a Python still-image prototype that proves the
reading algorithm against hand-read ground truth before any iOS work. See `CLAUDE.md` for
the full design and the two-stage plan.

**Not a diagnostic device - always verify against the physical scale.**

## Status
Vertical scale (Kopf 957), four hand-read positions across very different captures, all
inside the 0.1 mm (one-vernier-division) gate. Two read paths are validated: **manual**
(hand-tuned crop) and **auto** (deskew + bands detected from just a loose ROI).

| fixture | hand-read | manual | auto | notes |
|---------|-----------|--------|------|-------|
| `image3` | 40.4 mm | 40.421 mm | 40.381 mm | native resolution |
| `image2` | 16.1 mm | 16.077 mm | 16.101 mm | 3024x4032 + perforated background, `downscale=3` |
| `image1` | 63.8 mm | 63.759 mm | 63.856 mm | 640x480 low-res wide shot (EXIF-rotated), `upscale=3` |
| `image4` | 63.6 mm | -         | 63.587 mm | 640x480 low-res wide shot, auto-located only, `upscale=3` |

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
.venv/Scripts/python scripts/run_read.py image3 image2 image1   # manual crop
.venv/Scripts/python scripts/run_read.py --auto image3 image2 image1   # auto-locate from ROI
.venv/Scripts/python -m pytest tests/                    # validate both paths vs ground truth
```

## Fixtures
- `SampleImages/` - source photos.
- `fixtures/crops.json` - per-image scale factor, loose `roi`, the coarse anchor value, plus
  the hand-tuned deskew/bands used by the manual path (the auto path overrides these).
- `fixtures/ground_truth.json` - hand-read true value + tolerance per image.

## Not yet done
- **Full perspective warp**: the iterative deskew removes rotation robustly, but the main
  pitch still drifts along the scale (and image1's oblique shot compresses the vernier).
  `read.py` absorbs this with a local pitch fit and all reads pass comfortably, but a true
  4-point homography rectification would further tighten the wide/oblique cases.
- **Auto ROI**: the loose ROI is still supplied per fixture (the app gets it from the framing
  quality-gate / Vision rectangle detection); full-frame scale detection is out of scope here.
- OCR cross-check of the printed numbers (the coarse integer is anchored manually for now).
- The iOS app (Stage 2).
