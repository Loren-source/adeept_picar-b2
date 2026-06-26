#!/usr/bin/env python3
# coding: utf-8
"""
obstacle_labyrinthe.py
Main maze-solving loop for the Adeept PiCar-B2.

Behaviour:
  1. Drive forward continuously.
  2. Stop when the ultrasonic sensor detects a wall at DIST_MIN–DIST_MAX cm.
  3. Capture a frame every CAPTURE_INTERVAL seconds and detect the arrow direction.
  4. Steer and drive forward in the detected direction.
  5. If no arrow is recognised within ARROW_TIMEOUT seconds, back up and retry.

Run from the prog/ directory.
"""

import time

from ultra import Ultrasonic          # ultra.py  — ultrasonic distance sensor (returns mm)
from Caméra import Camera             # Caméra.py — provides capture_frame() for on-demand capture
                                      # Note: importing Caméra also calls move.setup() via
                                      #       CVThread class-level statements on import.
import move                           # move.py   — motor control
import RPIservo                       # RPIservo.py — servo control
from arrow_detector import detect_arrow   # arrow_detector.py — OpenCV arrow analysis

# ──────────────────────────────────────────────────────────────────────────────
# Tunable constants — adjust these for your maze and robot
# ──────────────────────────────────────────────────────────────────────────────
DIST_MIN         = 20    # cm: stop and read arrow when distance >= DIST_MIN
DIST_MAX         = 30    # cm: stop and read arrow when distance <= DIST_MAX
ARROW_TIMEOUT    = 5.0   # seconds: total time budget for arrow detection attempts
CAPTURE_INTERVAL = 0.5   # seconds: pause between frame captures during detection
TURN_ANGLE       = 90    # degrees: steering servo deflection for left/right turns

DRIVE_SPEED  = 20 # throttle % for driving forward  (0–100)
BACKUP_SPEED = 20    # throttle % for reversing
BACKUP_TIME  = 1.5   # seconds: how long to reverse when no arrow is found
TURN_HOLD    = 5   # seconds: hold steering angle while clearing a corner


# ──────────────────────────────────────────────────────────────────────────────
# Steering helper
# ──────────────────────────────────────────────────────────────────────────────
def steer(sc, direction):
    """
    Set the steering servo (servo ID 0) for the requested direction.

    Convention from Caméra.py / camera_opencv.py:
      moveAngle(0, +TURN_ANGLE) → turn left
      moveAngle(0, -TURN_ANGLE) → turn right
      moveAngle(0,  0)          → straight ahead
    """
    if direction == 'left':
        sc.moveAngle(0, TURN_ANGLE)
    elif direction == 'right':
        sc.moveAngle(0, -TURN_ANGLE)
    else:
        sc.moveAngle(0, 0)


# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # ── Hardware initialisation ───────────────────────────────────────────────

    # Ultrasonic sensor (GPIO 23 = trigger, 24 = echo — ultra.py defaults)
    ultrasonic = Ultrasonic()

    # Steering servo controller (servo ID 0 = front steering).
    # Caméra import already called move.setup() via CVThread class-level statements.
    sc = RPIservo.ServoCtrl()
    sc.moveInit()         # centre all servos to their neutral positions
    steer(sc, 'forward')  # ensure steering is straight before we start

    # Trigger the first camera capture now so Picamera2 initialises (2 s warm-up
    # is handled inside Camera.capture_frame() on its first call).
    print("Starting camera (Caméra.py — first frame triggers 2 s warm-up)...")
    Camera.capture_frame()   # discard first frame; auto-exposure stabilises inside
    print("Camera ready.\n")

    print("Maze solver running — press Ctrl+C to stop.\n")

    try:
        while True:
            # ── Step 1: drive forward ─────────────────────────────────────────
            # video_Tracking_Move controls both motor banks (M1 + M2).
            # direction=1 → forward,  direction=-1 → backward.
            steer(sc, 'forward')
            move.video_Tracking_Move(DRIVE_SPEED, 1)

            # ── Step 2: check distance ────────────────────────────────────────
            # ultra.py returns millimetres; divide by 10 to get centimetres.
            dist = ultrasonic.get_distance() / 10.0
            print(f"Distance: {dist:.1f} cm")

            if dist < DIST_MIN:
                # Too close to the wall — reverse slowly until back in the target zone
                print(f"  Too close ({dist:.1f} cm) — reversing to reach {DIST_MIN}–{DIST_MAX} cm zone...")
                move.video_Tracking_Move(BACKUP_SPEED, -1)
                while ultrasonic.get_distance() / 10.0 < DIST_MIN:
                    time.sleep(0.05)
                move.motorStop()
                continue

            if DIST_MIN <= dist <= DIST_MAX:
                # Wall is in the target range: stop and look for the direction arrow
                move.motorStop()
                print(f"  Wall at {dist:.1f} cm — reading arrow...")

                # ── Step 3: capture frames at intervals until arrow is found ──
                # Camera.capture_frame() returns one BGR numpy array on demand —
                # the camera does NOT stream between calls.
                direction = None
                deadline  = time.time() + ARROW_TIMEOUT

                while time.time() < deadline:
                    frame     = Camera.capture_frame()
                    direction = detect_arrow(frame)

                    if direction is not None:
                        print(f"  Arrow detected: {direction}")
                        # Stop the camera immediately so the internal buffer stops
                        # filling — mid-turn frames would corrupt the next detection.
                        Camera.stop_capture()
                        break

                    # Wait before the next capture attempt
                    time.sleep(CAPTURE_INTERVAL)

                if direction is None:
                    # ── Step 5: no arrow found — reverse slightly and retry ────
                    print(f"  No arrow found after {ARROW_TIMEOUT:.0f} s — reversing to retry...")
                    steer(sc, 'forward')
                    move.video_Tracking_Move(BACKUP_SPEED, -1)   # reverse
                    time.sleep(BACKUP_TIME)
                    move.motorStop()
                    continue   # restart the main loop

                # ── Step 4: back up briefly before turning ───────────────────
                # Camera is already stopped — no frames accumulate during this.
                print(f"  Backing up before turn...")
                steer(sc, 'forward')
                move.video_Tracking_Move(BACKUP_SPEED, -1)
                time.sleep(BACKUP_TIME)
                move.motorStop()

                # ── Step 5: steer and drive through the junction ──────────────
                print(f"  Turning {direction} and advancing through corner...")
                steer(sc, direction)
                time.sleep(0.5)     # let wheels reach their angle before driving
                move.video_Tracking_Move(DRIVE_SPEED, 1)
                time.sleep(TURN_HOLD)   # hold steering angle while clearing the corner
                steer(sc, 'forward')    # straighten up once through
                move.motorStop()

                # Restart the camera now that the robot is aligned in the new
                # corridor — 0.5 s settle time is handled inside start_capture().
                Camera.start_capture()

            # Brief delay to avoid hammering the distance sensor
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        # Always release hardware on exit
        move.motorStop()
        steer(sc, 'forward')
        move.destroy()    # deinitialises the PCA9685 motor driver
        print("Shutdown complete.")


if __name__ == '__main__':
    main()