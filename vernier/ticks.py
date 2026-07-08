"""Step 2: sub-pixel tick positions.

Detect dips in the intensity profile, then refine each to sub-pixel resolution
by fitting a parabola to the extremum and its two neighbours (vertex = tick
centre). This sub-pixel precision is what makes the global fit in step 4 work.
"""
import numpy as np
from scipy.signal import find_peaks


def find_ticks(profile, min_distance, prominence=0.03):
    """Return sorted sub-pixel row positions of dark ticks.

    `min_distance` is the minimum spacing (px) between ticks — set a bit below
    the expected pitch. `prominence` rejects shallow noise dips.
    """
    inverted = profile.max() - profile          # dips -> peaks
    peaks, props = find_peaks(inverted, distance=min_distance, prominence=prominence)
    centres = np.array([_parabolic_vertex(inverted, p) for p in peaks])
    return centres, props


def _parabolic_vertex(y, i):
    """Sub-pixel location of the peak near integer index `i`."""
    if i <= 0 or i >= len(y) - 1:
        return float(i)
    ym1, y0, yp1 = y[i - 1], y[i], y[i + 1]
    denom = ym1 - 2.0 * y0 + yp1
    if denom == 0:
        return float(i)
    return i + 0.5 * (ym1 - yp1) / denom
