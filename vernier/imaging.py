"""Step 0: load, deskew, and slice the scale into bands.

The prototype assumes a *roughly* rectified crop (long edges vertical). A small
residual rotation still blunts the 1-D dips, so we estimate and remove it before
collapsing to profiles.
"""
import numpy as np
from PIL import Image
from skimage.transform import rotate


def load_gray(path, downscale=1):
    """Load an image as a float grayscale array in [0, 1].

    `downscale` (int > 1) shrinks the image by that factor with a high-quality
    filter — useful for very high-res captures (the app downscales frames too).
    All band coordinates in the fixture config are then in downscaled pixels.
    """
    img = Image.open(path).convert("L")
    if downscale and downscale != 1:
        w, h = img.size
        img = img.resize((w // downscale, h // downscale), Image.LANCZOS)
    return np.asarray(img).astype(float) / 255.0


def estimate_skew(gray, rows=None, angle_range=(-8.0, 8.0), step=0.25):
    """Rotation (degrees) that makes the horizontal ticks sharpest.

    Metric: variance of the column-mean profile. When ticks are perfectly
    horizontal their dips line up across all rows, deepening the profile and
    maximising its variance.
    """
    r0, r1 = rows if rows is not None else (0, gray.shape[0])
    angles = np.arange(angle_range[0], angle_range[1] + 1e-9, step)

    def score(ang):
        d = rotate(gray, ang, resize=False, mode="edge")
        return float(d[r0:r1].mean(axis=1).var())

    return float(max(angles, key=score))


def deskew(gray, angle):
    """Rotate by `angle` degrees (positive = counter-clockwise)."""
    return rotate(gray, angle, resize=False, mode="edge")


def extract_band(gray, rows, cols):
    """Slice a (rows, cols) sub-rectangle — one scale's tick column."""
    (r0, r1), (c0, c1) = rows, cols
    return gray[r0:r1, c0:c1]
