"""
arrow_detector.py
Detect the direction of an arrow in a camera frame using two independent
methods that must agree before a direction is returned.
"""

import cv2
import numpy as np

MIN_IMBALANCE = 2   # minimum corner-count difference to consider a direction reliable


def _preprocess(frame):
    """
    Shared pipeline: BGR → gray → Gaussian blur → Otsu threshold (inverted) → morphological close.
    Returns a binary uint8 image where the arrow silhouette is white (255).
    """
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)


def detect_arrow(frame):
    """
    Analyse a camera frame using two independent checks and return the arrow direction.

    Method 1 — corner count:
        goodFeaturesToTrack finds corners; the arrowhead (triangle) produces more
        corners than the body (rectangle) on its side of the centroid.

    Method 2 — pixel count:
        White pixels are split at the same centroid X.  The arrowhead side has
        more pixels because the triangle spreads wider than the body.

    Returns:
        'left'     — both methods agree the arrowhead is on the left.
        'right'    — both methods agree the arrowhead is on the right.
        'conflict' — an arrow was detected but the two methods disagree.
                     The caller should back up, realign, and try again.
        None       — no arrow detected (too few corners or insufficient imbalance).
    """
    if frame is None:
        return None

    binary = _preprocess(frame)

    corners = cv2.goodFeaturesToTrack(
        binary,
        maxCorners=50,
        qualityLevel=0.01,
        minDistance=10,
        blockSize=7
    )

    if corners is None or len(corners) < 4:
        return None

    pts = corners.reshape(-1, 2).astype(np.float32)
    cx  = pts[:, 0].mean()

    # ── Method 1: corner count ────────────────────────────────────────────────
    right_corners = int(np.sum(pts[:, 0] > cx))
    left_corners  = int(np.sum(pts[:, 0] < cx))

    if abs(right_corners - left_corners) < MIN_IMBALANCE:
        return None   # corner distribution too symmetric — no confident reading

    corner_dir = 'right' if right_corners > left_corners else 'left'

    # ── Method 2: pixel count ─────────────────────────────────────────────────
    # Split the binary image at the corner centroid column.
    # The arrowhead (wider triangle) produces more white pixels on its side.
    col          = int(round(cx))
    left_pixels  = int(np.count_nonzero(binary[:, :col]))
    right_pixels = int(np.count_nonzero(binary[:, col:]))

    pixel_dir = 'right' if right_pixels > left_pixels else 'left'

    # ── Cross-check ───────────────────────────────────────────────────────────
    if corner_dir != pixel_dir:
        return 'conflict'

    return corner_dir


def get_arrow_centroid_offset(frame):
    """
    Return the horizontal pixel offset of the detected arrow's corner centroid
    from the frame centre.  Positive = arrow is to the right of centre.
    Returns None if no arrow can be detected (fewer than 4 corners found).
    """
    if frame is None:
        return None

    binary = _preprocess(frame)

    corners = cv2.goodFeaturesToTrack(
        binary, maxCorners=50, qualityLevel=0.01, minDistance=10, blockSize=7
    )
    if corners is None or len(corners) < 4:
        return None

    pts = corners.reshape(-1, 2).astype(np.float32)
    centroid_x     = pts[:, 0].mean()
    frame_center_x = frame.shape[1] / 2.0
    return centroid_x - frame_center_x
