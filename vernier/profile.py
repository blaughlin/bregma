"""Step 1: collapse a 2-D band to a 1-D intensity profile.

Averaging across the width of the band is the first big noise reduction. Dark
ticks become dips (low intensity). Blown-out specular glare is masked before
averaging and interpolated across so it can't create false minima.
"""
import numpy as np


def band_profile(strip, glare_thresh=0.98):
    """Mean intensity per row (low = dark tick), glare-masked.

    Returns a 1-D array the same length as the band's row extent.
    """
    masked = np.where(strip >= glare_thresh, np.nan, strip)
    with np.errstate(invalid="ignore"):
        prof = np.nanmean(masked, axis=1)

    # Rows that were entirely glare come back NaN — fill by interpolation.
    nan = np.isnan(prof)
    if nan.any() and (~nan).sum() >= 2:
        idx = np.arange(prof.size)
        prof[nan] = np.interp(idx[nan], idx[~nan], prof[~nan])
    return prof
