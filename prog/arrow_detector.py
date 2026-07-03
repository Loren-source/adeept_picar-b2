"""
arrow_detector.py
Detect the direction of an arrow using two independent geometric checks.
"""

import cv2
import numpy as np

MIN_IMBALANCE       = 2     # minimum corner-count asymmetry to be confident
ARROW_MIN_AREA      = 800   # px²: smallest contour accepted as the arrow
ARROW_MAX_AREA_FRAC = 0.45  # fraction of frame area: largest contour accepted


def _preprocess(frame):
    """
    BGR frame → binary image where the arrow silhouette is white (255).

    Larger blur and a close+open sequence give a cleaner, gap-free silhouette
    while removing isolated noise specks.
    """
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # THRESH_BINARY_INV: dark arrow on light background → arrow becomes white
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Close: fill small gaps inside the arrow silhouette
    close_k = np.ones((5, 5), np.uint8)
    binary  = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_k, iterations=2)

    # Open: remove isolated noise blobs smaller than the open kernel
    open_k = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_k, iterations=1)

    return binary


def _find_arrow_contour(binary):
    """
    Return the contour most likely to be the arrow, or None.

    Filters candidates by:
      - area: between ARROW_MIN_AREA and ARROW_MAX_AREA_FRAC × frame area
      - aspect ratio: bounding-box width/height between 0.3 and 6.0
        (excludes thin vertical lines and near-square blobs)

    Among candidates, returns the one with the largest area.
    """
    h, w    = binary.shape
    max_area = ARROW_MAX_AREA_FRAC * h * w

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if not (ARROW_MIN_AREA <= area <= max_area):
            continue
        _, _, cw, ch = cv2.boundingRect(cnt)
        aspect = cw / max(ch, 1)
        if 0.3 <= aspect <= 6.0:
            candidates.append(cnt)

    return max(candidates, key=cv2.contourArea) if candidates else None


def detect_arrow(frame):
    """
    Analyse a camera frame and return the arrow direction.

    Two independent methods must agree:

    Method 1 — corner count (Shi-Tomasi):
        goodFeaturesToTrack finds corners; the arrowhead (triangle) produces
        more detectable corners on its side of the corner centroid than the
        body (rectangle) does on its side.  The half with more corners is the
        arrowhead direction.

    Method 2 — mass offset:
        The arrowhead (a wider triangle) shifts the contour's centre of mass
        toward itself relative to the geometric centre of its bounding box.
        If  centroid_x > bbox_centre_x  the arrowhead is on the right.

    Returns:
        'left'     — both methods agree the arrowhead faces left.
        'right'    — both methods agree the arrowhead faces right.
        'conflict' — arrow detected but methods disagree; caller should
                     back up, realign, and retry.
        None       — no arrow found (too few corners or no qualifying contour).
    """
    if frame is None:
        return None

    binary = _preprocess(frame)

    # Both methods must look at the same object. Find the arrow's contour
    # first and mask everything else out, so corner detection (Method 1)
    # can't be thrown off by unrelated white regions elsewhere in the frame
    # (shadows, floor texture, wall seams) the way it would on the raw
    # binary image.
    contour = _find_arrow_contour(binary)
    if contour is None:
        return None

    arrow_mask = np.zeros_like(binary)
    cv2.drawContours(arrow_mask, [contour], -1, 255, thickness=cv2.FILLED)

    # ── Method 1: corner count ────────────────────────────────────────────────
    corners = cv2.goodFeaturesToTrack(
        arrow_mask,
        maxCorners=50,
        qualityLevel=0.01,
        minDistance=10,
        blockSize=7
    )
    if corners is None or len(corners) < 4:
        return None

    pts = corners.reshape(-1, 2).astype(np.float32)
    cx  = pts[:, 0].mean()   # corner centroid: sits between head and body clusters

    right_corners = int(np.sum(pts[:, 0] > cx))
    left_corners  = int(np.sum(pts[:, 0] < cx))

    if abs(right_corners - left_corners) < MIN_IMBALANCE:
        return None   # distribution too symmetric — no confident reading

    corner_dir = 'right' if right_corners > left_corners else 'left'

    # ── Method 2: mass offset vs bounding-box centre ─────────────────────────
    M = cv2.moments(contour)
    if M['m00'] == 0:
        return None

    centroid_x    = M['m10'] / M['m00']
    rx, _, rw, _  = cv2.boundingRect(contour)
    bbox_centre_x = rx + rw / 2.0

    # The arrowhead (wider) pulls the centre of mass toward itself.
    mass_dir = 'right' if centroid_x > bbox_centre_x else 'left'

    # ── Cross-check ───────────────────────────────────────────────────────────
    if corner_dir != mass_dir:
        return 'conflict'

    return corner_dir
