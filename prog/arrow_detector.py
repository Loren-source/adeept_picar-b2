"""
arrow_detector.py
Detect the direction of an arrow in a camera frame using goodFeaturesToTrack.
"""

import cv2
import numpy as np


def detect_arrow(frame):
    """
    Analyse a camera frame and return the direction of a visible arrow.

    Algorithm:
      1. Binarise the frame to isolate the arrow silhouette.
      2. Detect corners with goodFeaturesToTrack.
      3. Split corners into left/right and up/down halves around the centroid.
      4. The arrowhead (triangle) always has more corners than the body
         (rectangle): ~5 corners on the head side vs ~2 on the body side.
         The half with more corners is therefore the arrowhead direction.
      5. The axis (horizontal vs vertical) with the larger count imbalance
         determines whether the arrow is left/right or forward.

    Args:
        frame: NumPy array from Picamera2.capture_array().

    Returns:
        'left', 'right', or None if detection is not confident.
    """
    if frame is None:
        return None

    # ── Step 1: Pre-processing ────────────────────────────────────────────────
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # THRESH_BINARY_INV makes a dark arrow on a light background white,
    # which is what goodFeaturesToTrack needs.  Otsu picks the threshold.
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Close small gaps inside the silhouette for cleaner corner detection
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # ── Step 2: Corner detection ──────────────────────────────────────────────
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

    # ── Step 3: Count corners on each side of the centroid ───────────────────
    # The centroid of the detected corners acts as the dividing line.
    # It sits between the arrowhead and the body automatically.
    centroid = pts.mean(axis=0)   # (cx, cy)

    right_count = int(np.sum(pts[:, 0] > centroid[0]))
    left_count  = int(np.sum(pts[:, 0] < centroid[0]))
    up_count    = int(np.sum(pts[:, 1] < centroid[1]))   # y is downward in image
    down_count  = int(np.sum(pts[:, 1] > centroid[1]))

    h_diff = abs(right_count - left_count)   # horizontal imbalance
    v_diff = abs(up_count    - down_count)   # vertical imbalance

    # ── Step 4 & 5: Pick the dominant axis and arrowhead side ────────────────
    # Require a minimum imbalance of 2 to avoid returning a direction
    # when the corner distribution is nearly symmetric (ambiguous frame).
    MIN_IMBALANCE = 2

    if h_diff < MIN_IMBALANCE and v_diff < MIN_IMBALANCE:
        return None   # not confident enough

    # Only horizontal arrows are expected; vertical imbalance is ignored.
    return 'right' if right_count > left_count else 'left'