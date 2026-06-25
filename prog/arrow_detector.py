"""
arrow_detector.py
Detect the direction of an arrow in a camera frame using OpenCV corner detection.
"""

import cv2
import numpy as np


def detect_arrow(frame):
    """
    Analyse a BGR camera frame and return the direction of a visible arrow.

    Algorithm (geometric approach using goodFeaturesToTrack):
      1. Convert to grayscale and binarise to isolate the arrow silhouette.
      2. Detect strong corners with goodFeaturesToTrack — arrow shapes produce
         distinctive corners at the arrowhead tip and body vertices.
      3. Compute the centroid of all detected corner points.
      4. The corner farthest from the centroid is the arrow-tip candidate,
         because the tip is the most isolated extreme point of the shape.
      5. The vector centroid → tip gives the arrow direction.

    Args:
        frame: BGR (or RGB) image as a NumPy array, e.g. from Picamera2.capture_array().

    Returns:
        'left', 'right', 'forward', or None if detection fails or is ambiguous.
    """
    if frame is None:
        return None

    # ── Step 1: Pre-processing ────────────────────────────────────────────────
    # Convert to grayscale — arrow direction depends only on shape, not colour
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Gaussian blur suppresses pixel noise without destroying the arrow's edges
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Otsu's thresholding automatically picks the optimal threshold to separate
    # a dark arrow from a lighter background (or vice-versa with THRESH_BINARY_INV)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological closing fills small gaps inside the arrow silhouette so
    # the corners of the shape are cleaner
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    # ── Step 2: Corner detection ──────────────────────────────────────────────
    # goodFeaturesToTrack returns the N strongest "Shi-Tomasi" corners.
    # An arrow shape reliably produces corners at the three arrowhead vertices
    # (including the tip) and at the four corners of the rectangular body.
    corners = cv2.goodFeaturesToTrack(
        binary,
        maxCorners=50,      # upper limit; we use the statistical spread, not every point
        qualityLevel=0.01,  # accept corners with at least 1 % of the best corner's quality
        minDistance=10,     # discard corners closer than 10 px to each other
        blockSize=7         # pixel neighbourhood used to compute corner quality
    )

    if corners is None or len(corners) < 4:
        # Too few corners — likely no arrow visible or too much noise
        return None

    # Reshape from (N, 1, 2) to (N, 2): each row is an (x, y) coordinate
    pts = corners.reshape(-1, 2).astype(np.float32)

    # ── Step 3: Centroid of the corner point cloud ────────────────────────────
    centroid = pts.mean(axis=0)   # (cx, cy)

    # ── Step 4: Identify the arrow tip ───────────────────────────────────────
    # The arrowhead tip is geometrically isolated — it is the single extreme
    # point that protrudes farthest from the body, so it sits farthest from
    # the centroid of all corners.
    dists = np.linalg.norm(pts - centroid, axis=1)
    max_dist = float(np.max(dists))

    # If the farthest corner is not clearly separated (< 20 px from centroid),
    # the point cloud is too compact to be an arrow — return None
    if max_dist < 20:
        return None

    tip = pts[np.argmax(dists)]   # (x, y) of the arrow tip

    # ── Step 5: Map centroid → tip vector to a cardinal direction ─────────────
    # Image coordinate system: x increases to the right, y increases downward.
    dx = float(tip[0] - centroid[0])   # positive = tip is to the right
    dy = float(tip[1] - centroid[1])   # positive = tip is below centroid

    # The dominant axis (horizontal vs. vertical) determines the direction:
    #   |dx| > |dy|  →  arrow is mainly horizontal  →  left or right
    #   |dy| > |dx|  →  arrow is mainly vertical:
    #                     tip above centroid (dy < 0) = arrow pointing up = forward
    #                     tip below centroid (dy > 0) = downward arrow (unused)
    if abs(dx) > abs(dy):
        return 'right' if dx > 0 else 'left'
    else:
        return 'forward' if dy < 0 else None