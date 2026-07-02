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
from servo import servo_dir            # servo.py  — module-level Adafruit Servo on CANAL_DIRECTION
from arrow_detector import detect_arrow, get_arrow_centroid_offset

# ──────────────────────────────────────────────────────────────────────────────
# Tunable constants — adjust these for your maze and robot
# ──────────────────────────────────────────────────────────────────────────────
DIST_MIN         = 38    # cm: stop and read arrow when distance >= DIST_MIN
DIST_MAX         = 40    # cm: stop and read arrow when distance <= DIST_MAX
ARROW_TIMEOUT    = 5.0   # seconds: total time budget for arrow detection attempts
CAPTURE_INTERVAL = 0.5   # seconds: pause between frame captures during detection

# Absolute servo angles for channel 0 (steering) — same scale as tache11.py.
# Centre is slightly above 90 to match the physical servo neutral.
ANGLE_CENTER = 97    # straight ahead
ANGLE_LEFT   = 130   # full left turn
ANGLE_RIGHT  = 65    # full right turn

DRIVE_SPEED  = 30    # throttle % for driving forward  (0–100)
TURN_SPEED   = 45    # throttle % during cornering — needs more torque than straight driving
BACKUP_SPEED = 20    # throttle % for reversing
BACKUP_TIME  = 0.5     # seconds: how long to reverse when no arrow is found
TURN_HOLD    = 1.4   # seconds: hold steering angle while clearing a corner
TURN_HOLD_OPPOSITE = 0.6

TURN_OBSTACLE_DIST         = 30   # cm: if obstacle closer than this during a turn, interrupt
TURN_OBSTACLE_BACKUP_TIME  = 0.3  # seconds: how long to reverse after an obstacle mid-turn

ALIGN_THRESHOLD_PX = 40   # pixels: max acceptable centroid offset from frame centre (frame ~640 px wide)
ALIGN_NUDGE_FWD    = 0.12 # seconds: forward arc duration per alignment nudge
ALIGN_NUDGE_BWD    = 0.06 # seconds: backward arc duration per alignment nudge
ALIGN_MAX_ITER     = 5    # max nudge attempts before giving up and using best reading


# ──────────────────────────────────────────────────────────────────────────────
# Steering helper
# ──────────────────────────────────────────────────────────────────────────────
def steer(direction):
    """Set the steering servo angle via the module-level servo_dir from servo.py."""
    if direction == 'left':
        servo_dir.angle = ANGLE_LEFT
    elif direction == 'right':
        servo_dir.angle = ANGLE_RIGHT
    else:
        servo_dir.angle = ANGLE_CENTER

def opposite_direction(direction):
    if direction == 'left':
        direction = 'right'
        return direction
    if direction == 'right':
        direction = 'left'
    return direction


# ──────────────────────────────────────────────────────────────────────────────
# Turn with mid-turn obstacle check
# ──────────────────────────────────────────────────────────────────────────────
def turn_with_obstacle_check(ultrasonic, direction, duration, duration_opposite, speed, repetitions=2):
    """
    Perform `repetitions` alternating forward/backward arcs to complete a turn.
    Each forward arc lasts duration/repetitions seconds steered toward `direction`;
    each backward arc lasts duration_opposite/repetitions seconds steered opposite.
    """
    poll_interval = 0.05
    fwd_slice = duration / repetitions
    bwd_slice = duration_opposite / repetitions

    for _ in range(repetitions):
        steer(direction)
        move.video_Tracking_Move(speed, 1)
        remaining = fwd_slice
        while remaining > 0:
            t0 = time.time()
            time.sleep(min(poll_interval, remaining))
            remaining -= time.time() - t0

        move.motorStop()
        time.sleep(0.2)

        steer(opposite_direction(direction))
        move.video_Tracking_Move(speed, -1)
        remaining = bwd_slice
        while remaining > 0:
            t0 = time.time()
            time.sleep(min(poll_interval, remaining))
            remaining -= time.time() - t0

        move.motorStop()
        time.sleep(0.2)


# ──────────────────────────────────────────────────────────────────────────────
# Alignment: centre the robot on the arrow before committing to a turn
# ──────────────────────────────────────────────────────────────────────────────
def align_with_arrow():
    """
    Nudge the robot left or right (tiny forward-arc + backward-arc) until the
    detected arrow centroid is within ALIGN_THRESHOLD_PX of the frame centre.
    The camera must already be running when this is called.

    Returns the arrow direction from the final centred frame, or None if the
    arrow is lost during alignment (caller should fall back to the pre-alignment
    reading).
    """
    for attempt in range(1, ALIGN_MAX_ITER + 1):
        frame  = Camera.capture_frame()
        offset = get_arrow_centroid_offset(frame)

        if offset is None:
            print(f"  Align [{attempt}/{ALIGN_MAX_ITER}]: arrow lost — keeping pre-alignment direction.")
            return None

        print(f"  Align [{attempt}/{ALIGN_MAX_ITER}]: centroid offset {offset:+.0f} px")

        if abs(offset) <= ALIGN_THRESHOLD_PX:
            print(f"  Align: centred — taking final reading.")
            return detect_arrow(frame)

        # Arrow right of centre → robot is facing slightly left → nudge right
        nudge = 'right' if offset > 0 else 'left'
        steer(nudge)
        move.video_Tracking_Move(DRIVE_SPEED, 1)
        time.sleep(ALIGN_NUDGE_FWD)
        move.motorStop()
        time.sleep(0.1)

        steer(opposite_direction(nudge))
        move.video_Tracking_Move(DRIVE_SPEED, -1)
        time.sleep(ALIGN_NUDGE_BWD)
        move.motorStop()
        time.sleep(0.1)

    # Max iterations reached — take one last reading with whatever position we're at
    print(f"  Align: max iterations reached — taking best-effort reading.")
    frame = Camera.capture_frame()
    return detect_arrow(frame)


# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # ── Hardware initialisation ───────────────────────────────────────────────

    # Ultrasonic sensor (GPIO 23 = trigger, 24 = echo — ultra.py defaults)
    ultrasonic = Ultrasonic()

    steer('forward')  # ensure steering is straight before we start

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
            steer('forward')
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
                        print(f"  Arrow detected: {direction} — aligning...")
                        # Camera stays running so align_with_arrow() can capture frames.
                        aligned = align_with_arrow()
                        if aligned is not None:
                            direction = aligned
                        print(f"  Final direction after alignment: {direction}")
                        Camera.stop_capture()
                        break

                    # Wait before the next capture attempt
                    time.sleep(CAPTURE_INTERVAL)

                if direction is None:
                    # ── Step 5: no arrow found — reverse slightly and retry ────
                    print(f"  No arrow found after {ARROW_TIMEOUT:.0f} s — reversing to retry...")
                    steer('forward')
                    move.video_Tracking_Move(BACKUP_SPEED, -1)   # reverse
                    time.sleep(BACKUP_TIME)
                    move.motorStop()
                    continue   # restart the main loop

                # ── Step 4: steer and drive through the junction ─────────────
                print(f"  Turning {direction} and advancing through corner...")
                turn_with_obstacle_check(ultrasonic, direction, TURN_HOLD, TURN_HOLD_OPPOSITE, TURN_SPEED)
                steer('forward')    # straighten up once through

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
        servo_dir.angle = ANGLE_CENTER
        move.destroy()    # deinitialises the PCA9685 motor driver
        print("Shutdown complete.")


if __name__ == '__main__':
    main()