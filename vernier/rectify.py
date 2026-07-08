"""Perspective rectification from the tick grid (homography).

After deskew, the main scale still shows perspective: its ticks - equally spaced
and parallel in the real world - appear with a pitch that drifts along the scale
(foreshortening) and lines that aren't perfectly horizontal (keystone). We undo
both without finding the scale's physical corners, using the ticks themselves as
the calibration grid:

  * detect main-tick rows at a few sub-columns across the band,
  * match them into lines (one per tick),
  * fit a homography that sends every tick line to a horizontal, equally-spaced
    target row (columns left unchanged).

The homography is applied to the sub-pixel tick *coordinates* (not the pixels):
warping the image would resample every tick and blur the sub-pixel centres that
the 0.1 mm read depends on. Correcting coordinates keeps full precision and
treats the main and vernier bands consistently (same homography, their own
column).
"""
import numpy as np
from scipy.signal import find_peaks
from skimage.transform import ProjectiveTransform


def _dip_centers(profile, min_distance, prominence):
    """Sub-pixel positions of dark dips in a 1-D profile (parabolic vertex)."""
    inv = profile.max() - profile
    if inv.max() <= 0:
        return np.array([])
    peaks, _ = find_peaks(inv, distance=min_distance, prominence=prominence * inv.max())
    out = []
    for i in peaks:
        if 0 < i < len(inv) - 1:
            y0, y1, y2 = inv[i - 1], inv[i], inv[i + 1]
            den = y0 - 2 * y1 + y2
            out.append(i + 0.5 * (y0 - y2) / den if den != 0 else float(i))
        else:
            out.append(float(i))
    return np.array(out)


def _slice_ticks(gray, col_center, half_w, rows, dmin, prominence=0.1):
    r0, r1 = rows
    c0 = max(0, col_center - half_w)
    c1 = min(gray.shape[1], col_center + half_w)
    prof = gray[r0:r1, c0:c1].mean(axis=1)
    return _dip_centers(prof, dmin, prominence) + r0


def build_homography(gray, main_cols, rows, n_slices=3, slice_half=5):
    """Estimate the rectifying homography from the main-scale ticks.

    Returns (transform, target_pitch) or (None, None) if there aren't enough
    cleanly-matched ticks. `transform` maps source (image) coords -> rectified
    coords; apply it to tick points as ``tform(np.column_stack([cols, rows]))``.
    """
    c0, c1 = main_cols
    # seed pitch for peak spacing
    seed = _dip_centers(gray[rows[0]:rows[1], c0:c1].mean(axis=1), 4, 0.12)
    if len(seed) < 4:
        return None, None
    pitch = float(np.median(np.diff(np.sort(seed))))
    dmin = max(3, int(0.6 * pitch))

    cols = np.linspace(c0 + slice_half, c1 - slice_half, n_slices)
    ticks_per_col = [_slice_ticks(gray, int(round(cc)), slice_half, rows, dmin) for cc in cols]
    ref = ticks_per_col[len(cols) // 2]          # centre slice defines the indexing
    if len(ref) < 4:
        return None, None

    # index the reference ticks on a uniform grid (robust to a missed tick)
    k_ref = np.round((ref - ref[0]) / pitch).astype(int)
    a, b = np.polyfit(k_ref, ref, 1)             # a = uniform target pitch
    target_row = {k: b + a * k for k in range(k_ref.min() - 2, k_ref.max() + 3)}

    src, dst = [], []
    for cc, ticks in zip(cols, ticks_per_col):
        for t in ticks:
            k = int(round((t - b) / a))          # which tick index this is
            if k in target_row and abs((b + a * k) - t) < 0.45 * pitch:
                src.append((cc, t))              # (x=col, y=row)
                dst.append((cc, target_row[k]))  # same column, uniform row
    if len(src) < 8:
        return None, None

    tform = ProjectiveTransform()
    # source (image) -> rectified, applied to tick coordinates
    if not tform.estimate(np.array(src), np.array(dst)):
        return None, None
    return tform, float(a)


def rectify_rows(tform, col, rows):
    """Map tick rows detected at image column `col` to their rectified rows."""
    rows = np.asarray(rows, float)
    pts = np.column_stack([np.full(rows.shape, float(col)), rows])
    return tform(pts)[:, 1]
