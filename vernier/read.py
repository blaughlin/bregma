"""Steps 3-5: coarse reading, fine global-fit reading, and combine.

Both scales are fitted to *regular grids* before anything else. A grid fit
(row = pitch * index + offset, with iterative outlier rejection) repairs the
inevitable damage from real photos: a mis-located tick near an engraving, a
missed end tick, and — critically — it gives a clean local pitch immune to the
few spurious dips detection leaves behind.

The main scale has a mild perspective pitch gradient along its length, so its
pitch is measured *locally*, from the main ticks spanning the vernier only.

Coordinate note: image rows increase downward; the vernier is numbered from a
reference end (n=0). `vernier_ref` says which physical end that is.
"""
import numpy as np


def fit_grid(ticks, reject_sigma=2.5, iters=3):
    """Fit sorted tick positions to row = pitch*index + offset.

    Integer indices are assigned by rounding to the current pitch; a few
    iterations of least-squares + residual rejection lock onto the true grid
    even when some ticks are missing (index gaps) or mis-detected (outliers).

    Returns (pitch, offset, indices, inlier_mask) with indices/mask aligned to
    the sorted input.
    """
    t = np.sort(np.asarray(ticks, dtype=float))
    pitch = float(np.median(np.diff(t)))
    idx = np.round((t - t[0]) / pitch).astype(int)
    mask = np.ones(len(t), dtype=bool)
    a, b = pitch, t[0]
    for _ in range(iters):
        a, b = np.polyfit(idx[mask], t[mask], 1)   # t ≈ a*idx + b
        resid = t - (a * idx + b)
        s = np.std(resid[mask]) or 1e-9
        mask = np.abs(resid) <= reject_sigma * s
        idx = np.round((t - b) / a).astype(int)
    a, b = np.polyfit(idx[mask], t[mask], 1)
    return float(a), float(b), idx, mask


def _grid_pos(pitch, offset, index):
    return pitch * index + offset


def fine_reading(vernier_ticks, main_pitch, main_offset, vernier_ref,
                 resolution=0.1, reject_sigma=2.0):
    """Step 4: fine part by GLOBAL line fit of per-vernier-tick phase.

    Each vernier tick's offset to the nearest *regular main-grid* line grows
    linearly with the vernier number and wraps once across the vernier. Fit the
    line to all ticks (rejecting outliers by residual) and read the zero
    crossing -> aligned vernier number n* (fractional). fine = n* * resolution.
    """
    v = np.sort(np.asarray(vernier_ticks, float))
    # clean the vernier onto its own grid, then number from the reference end
    pv, cv, vidx, vmask = fit_grid(v)
    v = v[vmask]
    vidx = vidx[vmask]
    # n = 0 at the reference end
    if vernier_ref == "bottom":       # reference at largest row
        number = vidx.max() - vidx
    else:                             # reference at smallest row
        number = vidx - vidx.min()

    # signed offset (px) of each vernier tick to the nearest main-grid line
    k = np.round((v - main_offset) / main_pitch)
    offset = v - _grid_pos(main_pitch, main_offset, k)   # in (-pm/2, pm/2]

    order = np.argsort(number)
    n = number[order].astype(float)
    e = offset[order]
    e_u = np.unwrap(e * 2 * np.pi / main_pitch) * main_pitch / (2 * np.pi)

    # robust line fit: fit, reject worst residuals, refit
    mask = np.ones(len(n), bool)
    for _ in range(2):
        slope, intercept = np.polyfit(n[mask], e_u[mask], 1)
        resid = e_u - (slope * n + intercept)
        s = np.std(resid[mask]) or 1e-9
        mask = np.abs(resid) <= reject_sigma * s
    slope, intercept = np.polyfit(n[mask], e_u[mask], 1)

    period = main_pitch / abs(slope) if slope else np.inf   # ~ n-per-division (=10)
    n_star = (-intercept / slope) % period if slope else 0.0
    fine_mm = (n_star % (1.0 / resolution)) * resolution
    return {
        "fine_mm": float(fine_mm),
        "n_star": float(n_star),
        "slope": float(slope),
        "intercept": float(intercept),
        "number": n,
        "offset_u": e_u,
        "inliers": mask,
        "resid_rms": float(np.sqrt(np.mean((e_u[mask] - (slope * n[mask] + intercept)) ** 2))),
        "vernier_pitch": pv,
        "vernier_ref_row": float(cv if vernier_ref != "bottom"
                                 else _grid_pos(pv, cv, vidx.max())),
    }


def coarse_reading(vernier_zero_row, anchor, local_pitch, mm_per_div=1.0):
    """Step 3: integer/tens part = value of the main division at/just-below the
    vernier zero. Anchored by a known value (a numbered mark, or the integer the
    vernier-zero sits next to — OCR's job in the app).

    `anchor` = {"row": known_row, "value_mm": known_value}. Value grows as row
    decreases, at `local_pitch` px per division. The coarse part is the division
    at/just-below the vernier zero.
    """
    value_at_zero = anchor["value_mm"] + (anchor["row"] - vernier_zero_row) / local_pitch * mm_per_div
    return float(np.floor(value_at_zero / mm_per_div + 1e-6) * mm_per_div)


def read_scale(main_ticks, vernier_ticks, anchor, vernier_zero_row=None,
               mm_per_div=1.0, resolution=0.1, vernier_ref="bottom"):
    """Step 5: combine coarse + fine into the final mm reading.

    The vernier zero is taken from the *detected* reference tick unless
    `vernier_zero_row` is given. If `anchor` has no "row", it is anchored at the
    vernier zero (i.e. anchor["value_mm"] is the integer the zero sits next to).
    """
    m = np.sort(np.asarray(main_ticks, float))
    v = np.sort(np.asarray(vernier_ticks, float))

    # local main pitch: fit only the main ticks spanning the vernier region
    lo, hi = v.min(), v.max()
    span = hi - lo
    sel = (m > lo - 0.5 * span) & (m < hi + 0.5 * span)
    pm, bm, _, _ = fit_grid(m[sel])

    fine = fine_reading(v, pm, bm, vernier_ref, resolution)
    vzero = fine["vernier_ref_row"] if vernier_zero_row is None else vernier_zero_row
    anchor = dict(anchor)
    anchor.setdefault("row", vzero)

    coarse_mm = coarse_reading(vzero, anchor, pm, mm_per_div)
    fine_mm = fine["fine_mm"] % mm_per_div
    reading = coarse_mm + fine_mm
    return {
        "reading_mm": float(reading),
        "coarse_mm": float(coarse_mm),
        "fine_mm": float(fine_mm),
        "vernier_zero_row": float(vzero),
        "local_main_pitch": pm,
        "fine": fine,
    }
