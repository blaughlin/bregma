# Stereotax Vernier Reader — Design Notes

## Goal
An iPhone app that uses the camera to read a Kopf-style stereotaxic vernier scale in
real time and display the coordinate in large, high-contrast type. Primary motivation:
reduce eye strain from reading the physical vernier during surgery. Not a commercial
product — free / possibly open-source, valued as a self-use tool + portfolio piece.
**Not a diagnostic device: always verify against the physical scale.**

## Two-stage plan
1. **Python still-image prototype** (this repo, first) — prove the reading algorithm
   against known values on real photos before writing any iOS code.
2. **iOS app** (later) — port the proven algorithm; add the real-time camera guidance loop.

Do NOT start iOS work until the Python prototype gives a reading we trust on a real frame.

---

## Prototype: dependencies
- Python + NumPy + SciPy + scikit-image (grayscale, perspective warp, edge detection).
- **No OpenCV in the prototype.** The hard part (sub-pixel vernier fit) is custom signal
  math either way; OpenCV adds machinery without helping it. Keep it lightweight.
- Matplotlib for debugging — visual inspection of intermediate signals is most of the debugging.

## Test fixtures
- Commit the sample frame photo and, ideally, several photos of the scale at KNOWN
  positions as test fixtures. Each fixture's true value (read by hand) is the ground truth
  the algorithm is checked against on every iteration.

---

## The reading algorithm (steps 1–5)

Vernier principle being exploited: N vernier divisions span (N−1) main divisions, so each
vernier tick is offset from a main tick by a slightly different, linearly-growing amount.
Exactly one vernier tick aligns with a main tick — its number is the fractional digit.
The linear growth is what makes sub-pixel detection possible even when no pair looks
perfectly aligned by eye.

Assume input is a rectified, cropped strip of just the scale (long edges vertical,
perspective removed).

1. **Collapse to 1-D signals.** Sum pixel intensity across the width of the scale for each
   position along its length → dark ticks become dips in a 1-D intensity profile. Do this
   separately for the main scale and the vernier scale. (Averaging across width is the first
   big noise reduction; it's why rectification matters — skew smears ticks and blunts dips.)

2. **Sub-pixel tick positions.** For each dip, fit a parabola (or Gaussian) to the minimum
   and its two neighbors; the vertex gives the tick center at sub-pixel resolution. Produce
   two lists of precise positions (main ticks, vernier ticks).

3. **Coarse reading.** Locate the vernier's zero mark against the main scale → whole +
   first-decimal part (which main division the vernier-zero sits just past). Cross-check with
   OCR of the printed numbers to guard against miscounting a division.

4. **Fine reading by GLOBAL FIT (not "find the aligned tick").** For each vernier tick,
   compute offset to the nearest main tick. Plot offset vs. vernier tick index — theory says
   this is a straight line crossing zero at the aligned tick. Fit the line to ALL ticks and
   read off the zero crossing. Every tick contributes → robust, sub-division precision. This
   step is what interpolates within the nominal resolution. Line-fit residuals also reject
   outliers (junk features that aren't evenly spaced).

5. **Combine.** Coarse (step 3) + fine (step 4), using pixels-per-mm from the tick spacing
   as the unit bridge. Average the final value across N locked frames (in the app).

## Self-calibration (key for handheld distance-invariance)
Never rely on absolute pixels-per-mm from camera distance. Derive it LIVE from the known
true tick spacing every frame. The scale calibrates itself off the object it's reading.

## Robustness notes
- Glare creates false minima → mask blown-out specular patches before fitting, interpolate across.
- Non-tick features (center hole, "001132R" engraving) → restrict analysis to the graduated
  band; periodicity of real ticks + line-fit residuals reject the rest.
- **Need the vernier ratio for this frame**: how many vernier divisions span how many main
  divisions (e.g. 10 over 9 → 0.1 mm; 20 over ... → 0.05 mm). This constant is baked into
  step 4's expected slope and sets the final resolution. CONFIRM THIS EARLY.

## Debugging must-have
Render intermediate images: the rectified crop, and the 1-D profiles with detected tick
centers overlaid. Seeing the profile with tick positions marked is how the fits get debugged.

---

## iOS app (later stage)

### Framework decision
Default to **Apple-native: Vision + Accelerate. No OpenCV.**
- Vision: rectangle detection + rectification of the scale (it's essentially a rectangle),
  and OCR for printed numbers / coarse value.
- Accelerate / vDSP: all 1-D signal math (profile sums, parabola fits, line solve) — fast,
  dependency-free.
- Plays nicely with existing Swift / WWDC26 (App Intents, Foundation Models) work.
- **OpenCV held in reserve** only if Vision's scale detection can't cope with real-world
  glare/angles (adaptive thresholding, morphology, custom contours). Don't take the
  dependency until proven necessary.

### Real-time pipeline
Frame → downscale → detect & rectify scale → **quality gate** → (on pass) full-res vernier
read → stability buffer → lock & display.

Quality gate runs cheap at ~30fps; only triggers the expensive read when the frame passes.
Checks + the guidance they drive:
- **Framing** (scale detected & centered, both scales in frame) → move left/right/up/down.
- **Distance** (from detected tick pixel-spacing vs. known true spacing) → closer/farther.
  Need enough px per division to resolve the vernier sub-pixel.
- **Angle/skew** (from scale edges: parallel & vertical?) → tilt/rotate. Off-axis shears the
  vernier alignment and corrupts the read.
- **Focus** (variance of Laplacian on tick region) + **glare** (blown-out patches) → steady / reduce glare.
- **Stability** — require N consecutive good low-motion frames, then lock. Averaging across
  them beats down noise → helps hit 0.1 mm.

### UX for the eye-strain goal
Directional arrows + haptics (settling buzz as you approach the sweet spot, distinct
confirmation tap on lock) so the user feels their way in rather than squinting at guidance
text. Final reading renders large, high-contrast, and HOLDS on screen — never read live.
Consider quick mode vs. precise mode (tunable "good enough" threshold).

### Capture stack
AVFoundation (capture) + Vision (rectangle/OCR) + Accelerate (signal math).

---

## Scope discipline
Nail ONE axis / one scale end-to-end first — a real reading trusted against a known value —
before any multi-axis ambition. Open question to answer later: do all 3 axes use this same
vernier style, and read one-at-a-time or simultaneously? (Affects mount vs. single camera.)

## First concrete move in Claude Code
Write the step 1–5 read assuming a roughly-rectified crop. Run it against the sample photo.
Check output against the hand-read true value. Iterate on the fits using the overlaid-profile
debug images. Only then build outward (rectification front-end, then iOS).
