"""Front-end: automatically locate and rectify the vernier scale.

Replaces the hand-tuned per-fixture crop (deskew angle, main/vernier band columns,
vernier row range) with detection driven by the one thing that reliably marks a
graduated scale: **periodic dark ticks**.

Pipeline:
  1. Score every column by how periodic its vertical intensity profile is
     (autocorrelation peak) -> tick columns light up; smooth metal, background,
     and printed numbers do not.
  2. Estimate deskew from the tick columns only (immune to periodic backgrounds
     like image2's perforated panel that fool a whole-frame estimate).
  3. The main scale's ticks span the full height; the vernier's span a contiguous
     sub-region (the moving cursor). Main and vernier columns abut, so they are
     separated not by a column gap but by this per-column ROW COVERAGE: full-
     height columns are the main band, shorter-coverage columns the vernier band.

A loose ROI (as the app's framing quality-gate provides) confines the search and
keeps periodic backgrounds out.
"""
import numpy as np
from scipy.ndimage import uniform_filter1d
from skimage.transform import rotate


def _highpass(gray, win=25):
    """Remove slow vertical shading so only fine features (ticks, text) remain."""
    return gray - uniform_filter1d(gray, size=win, axis=0, mode="nearest")


def _rolling_std(x, win=9):
    m = uniform_filter1d(x, win, mode="nearest")
    return np.sqrt(np.clip(uniform_filter1d((x - m) ** 2, win, mode="nearest"), 0, None))


def column_tickiness(gray, min_lag=4, max_lag=45):
    """Per-column periodicity score and dominant pitch (px).

    score[c] = peak of the column profile's normalised autocorrelation over lags
    in [min_lag, max_lag]. High only when the column crosses regularly-spaced
    ticks; a printed digit is dark but not periodic, so it scores low.
    """
    hp = _highpass(gray)
    hp = hp - hp.mean(axis=0, keepdims=True)
    energy = np.einsum("rc,rc->c", hp, hp)
    norm = np.where(energy > 0, energy, 1.0)
    best = np.zeros(hp.shape[1])
    best_lag = np.zeros(hp.shape[1], dtype=int)
    for lag in range(min_lag, max_lag):
        acn = np.einsum("rc,rc->c", hp[:-lag], hp[lag:]) / norm
        upd = acn > best
        best[upd] = acn[upd]
        best_lag[upd] = lag
    best[energy <= 1e-9] = 0.0
    return best, best_lag.astype(float)


def _contiguous_runs(mask, min_len=3, max_gap=2):
    """Return [(start, end)] contiguous True runs, bridging gaps <= max_gap."""
    idx = np.where(mask)[0]
    if idx.size == 0:
        return []
    runs = []
    s = p = idx[0]
    for i in idx[1:]:
        if i - p <= max_gap + 1:
            p = i
        else:
            runs.append((s, p + 1)); s = p = i
    runs.append((s, p + 1))
    return [(a, b) for a, b in runs if b - a >= min_len]


def _largest_run(mask, **kw):
    runs = _contiguous_runs(mask, **kw)
    return max(runs, key=lambda r: r[1] - r[0]) if runs else None


def residual_skew(gray, cols, rows, angle_range=(-6.0, 6.0), step=0.2):
    """Residual tilt (deg) of the ticks in a band, by rotating a *crop* of the
    band about its centre and maximising the row-mean profile's variance (ticks
    horizontal -> deepest aligned dips). Estimated on the already-mostly-deskewed
    frame, so the search stays near 0 and column shear is negligible."""
    r0, r1 = rows
    c0, c1 = cols
    crop = gray[r0:r1, c0:c1]
    if crop.shape[1] < 6 or crop.shape[0] < 20:
        return 0.0
    m = int((c1 - c0) * 0.6) + 2
    angles = np.arange(angle_range[0], angle_range[1] + 1e-9, step)

    def score(ang):
        d = rotate(crop, ang, resize=False, mode="edge")
        prof = d[m:-m].mean(axis=1) if d.shape[0] > 2 * m else d.mean(axis=1)
        return float(prof.var())

    return float(max(angles, key=score))


def _column_coverage(gray, rows):
    """For each column, the length and extent of its longest tick-active row run
    within `rows` (blank metal is inactive; ticks are active)."""
    hp = _highpass(gray)
    r0, r1 = rows
    C = gray.shape[1]
    cov = np.zeros(C)
    start = np.zeros(C, int)
    end = np.zeros(C, int)
    for c in range(C):
        act = _rolling_std(hp[r0:r1, c])
        if act.max() <= 1e-6:
            continue
        runs = _contiguous_runs(act > 0.4 * act.max(), min_len=8, max_gap=12)
        if not runs:
            continue
        a, b = max(runs, key=lambda x: x[1] - x[0])
        cov[c] = b - a
        start[c] = a + r0
        end[c] = b + r0
    return cov, start, end


def _detect_bands(d, roi, score_thresh, main_frac):
    """On a deskewed image `d`, separate main and vernier bands by column row
    coverage. Returns (main_run, vern_run, cstart, cend, pitches) or raises."""
    R, C = d.shape
    r0, r1, c0, c1 = roi
    scores, pitches = column_tickiness(d)
    ticky = scores > score_thresh
    ticky[:c0] = False
    ticky[c1:] = False
    cov, cstart, cend = _column_coverage(d, (r0, r1))
    cov = cov * ticky
    if cov.max() <= 0:
        raise RuntimeError("no ticks found in ROI")
    maxcov = cov.max()

    main_run = _largest_run(cov > main_frac * maxcov, min_len=4, max_gap=2)
    vern_run = _largest_run((cov > 0.12 * maxcov) & (cov <= main_frac * maxcov),
                            min_len=4, max_gap=2)
    if main_run is None or vern_run is None:
        raise RuntimeError(f"could not separate bands (main={main_run}, vernier={vern_run})")
    return main_run, vern_run, cstart, cend, pitches


def locate_scale(gray, roi=None, score_thresh=0.30, main_frac=0.6, verbose=False):
    """Detect the scale; return {deskew_deg, rows, main_cols, vernier_cols,
    vernier_rows} in full-image coordinates.

    `roi` = (r0, r1, c0, c1): a loose bounding box around the scale.
    `main_frac`: columns covering > main_frac of the tallest coverage are the
    main scale; shorter ticky columns are the vernier cursor.

    Strategy: detect bands at angle 0, estimate skew from the clean full-height
    main band only, then re-detect on the deskewed image.
    """
    R, C = gray.shape
    roi = roi if roi is not None else (0, R, 0, C)
    r0, r1, c0, c1 = roi

    # Iterate: detect bands in the current (partly deskewed) frame, measure the
    # residual tilt of the main band, accumulate, repeat. Converges from any
    # starting tilt -- after the first correction the residual (and the column
    # shear it induces) is small, so band columns stay valid.
    angle = 0.0
    for _ in range(4):
        d = rotate(gray, angle, resize=False, mode="edge") if angle else gray
        main_run, vern_run, cstart, cend, pitches = _detect_bands(d, roi, score_thresh, main_frac)
        resid = residual_skew(d, main_run, (r0, r1))
        angle += resid
        if abs(resid) < 0.1:
            break

    # final detection in the converged frame
    d = rotate(gray, angle, resize=False, mode="edge") if angle else gray
    result = dict(deskew_deg=angle, **geometry(d, roi, score_thresh, main_frac))
    if verbose:
        print("locate:", result)
    return result


def geometry(d, roi, score_thresh=0.30, main_frac=0.6):
    """Band geometry (columns, rows, pitch) from an already-deskewed image `d`.
    Returned separately from deskew so it can be re-run after rectification."""
    main_run, vern_run, cstart, cend, pitches = _detect_bands(d, roi, score_thresh, main_frac)
    mc = np.arange(*main_run)
    vc = np.arange(*vern_run)
    return dict(
        rows=[int(np.median(cstart[mc])), int(np.median(cend[mc]))],
        main_cols=[int(main_run[0]), int(main_run[1])],
        vernier_cols=[int(vern_run[0]), int(vern_run[1])],
        vernier_rows=[int(np.median(cstart[vc])), int(np.median(cend[vc]))],
        main_pitch=float(np.median(pitches[mc])),
        vernier_pitch=float(np.median(pitches[vc])),
    )
