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
from servo import RobotServos          # servo.py  — RobotServos class, set_angle(canal, angle)
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
TURN_SPEED   = 30    # throttle % during cornering — needs more torque than straight driving
BACKUP_SPEED = 20    # throttle % for reversing
BACKUP_TIME  = 0.5     # seconds: how long to reverse when no arrow is found
TURN_HOLD    = 1.4   # seconds: hold steering angle while clearing a corner
TURN_HOLD_OPPOSITE = 0.6

TURN_OBSTACLE_DIST         = 30   # cm: if obstacle closer than this during a turn, interrupt
TURN_OBSTACLE_BACKUP_TIME  = 0.3  # seconds: how long to reverse after an obstacle mid-turn

ALIGN_THRESHOLD_PX = 40   # pixels: max acceptable centroid offset from frame centre (frame ~640 px wide)
ALIGN_SPEED        = 25   # throttle % for alignment nudges — slower than DRIVE_SPEED for finer correction
ALIGN_NUDGE_FWD    = 0.15 # seconds: forward arc per nudge — short, small correction step
ALIGN_NUDGE_BWD    = 0.15 # seconds: backward arc per nudge — equal to FWD so there is no net translation
ALIGN_MAX_ITER     = 5    # max nudge attempts before giving up and using best reading

CONFLICT_MAX_RETRY = 3    # max times to back up and realign after a corner/pixel conflict


# ──────────────────────────────────────────────────────────────────────────────
# Steering helper
# ──────────────────────────────────────────────────────────────────────────────
STEERING_CANAL = 0  # PCA9685 channel wired to the front steering servo

def steer(servos, direction):
    """Set the steering servo to the angle for direction via RobotServos.set_angle."""
    if direction == 'left':
        servos.set_angle(STEERING_CANAL, ANGLE_LEFT)
    elif direction == 'right':
        servos.set_angle(STEERING_CANAL, ANGLE_RIGHT)
    else:
        servos.set_angle(STEERING_CANAL, ANGLE_CENTER)

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
def turn_with_obstacle_check(ultrasonic, servos, direction, duration, duration_opposite, speed, repetitions=2):
    """
    Perform `repetitions` alternating forward/backward arcs to complete a turn.
    Each forward arc lasts duration/repetitions seconds steered toward `direction`;
    each backward arc lasts duration_opposite/repetitions seconds steered opposite.
    """
    poll_interval = 0.05
    fwd_slice = duration / repetitions
    bwd_slice = duration_opposite / repetitions

    for _ in range(repetitions):
        steer(servos, direction)
        time.sleep(0.3)          # let servo reach target angle before driving
        move.video_Tracking_Move(speed, 1)
        remaining = fwd_slice
        while remaining > 0:
            t0 = time.time()
            time.sleep(min(poll_interval, remaining))
            remaining -= time.time() - t0

        move.motorStop()
        time.sleep(0.3)          # let robot settle before reversing direction

        steer(servos, opposite_direction(direction))
        time.sleep(0.3)          # let servo reach opposite angle before driving
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
def _reposition_to_arrow(servos):
    """
    Nudge the robot left or right until the arrow centroid is within
    ALIGN_THRESHOLD_PX of the frame centre.  Does NOT read or return a
    direction — call detect_arrow() separately after this.
    Camera must already be running.

    Which physical steer direction actually reduces a positive offset
    depends on camera/servo/motor polarity that can vary per robot.
    `sign` starts assuming offset>0 -> steer right; if a nudge makes
    the offset worse instead of better, it flips for later nudges.
    """
    sign = 1
    prev_abs_offset = None

    for attempt in range(1, ALIGN_MAX_ITER + 1):
        frame  = Camera.capture_frame()
        offset = get_arrow_centroid_offset(frame)

        if offset is None:
            print(f"  Align [{attempt}/{ALIGN_MAX_ITER}]: arrow lost.")
            return

        print(f"  Align [{attempt}/{ALIGN_MAX_ITER}]: centroid offset {offset:+.0f} px")

        if abs(offset) <= ALIGN_THRESHOLD_PX:
            print(f"  Align: centred.")
            return

        # If the previous nudge made things worse (beyond noise), our
        # offset-to-steer mapping is backwards for this robot — flip it.
        if prev_abs_offset is not None and abs(offset) > prev_abs_offset + 5:
            sign = -sign
            print(f"  Align: previous nudge increased offset, flipping correction direction.")
        prev_abs_offset = abs(offset)

        steer_right = (offset > 0) if sign > 0 else (offset < 0)
        nudge = 'right' if steer_right else 'left'
        steer(servos, nudge)
        time.sleep(0.2)                              # servo settle before driving
        move.video_Tracking_Move(ALIGN_SPEED, 1)
        time.sleep(ALIGN_NUDGE_FWD)
        move.motorStop()

        steer(servos, opposite_direction(nudge))
        time.sleep(0.2)                              # servo settle before reversing
        move.video_Tracking_Move(ALIGN_SPEED, -1)
        time.sleep(ALIGN_NUDGE_BWD)
        move.motorStop()
        time.sleep(0.1)                              # brief settle before next measurement

    print(f"  Align: max iterations reached.")


def align_with_arrow(servos):
    """
    Centre the robot on the arrow, then return the detected direction.
    Never returns 'conflict' — if the dual-check still disagrees after
    repositioning, returns None so the caller falls back gracefully.
    """
    _reposition_to_arrow(servos)
    frame  = Camera.capture_frame()
    result = detect_arrow(frame)
    return result if result in ('left', 'right') else None


# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # ── Hardware initialisation ───────────────────────────────────────────────

    # Ultrasonic sensor (GPIO 23 = trigger, 24 = echo — ultra.py defaults)
    ultrasonic = Ultrasonic()

    servos = RobotServos()
    steer(servos, 'forward')  # ensure steering is straight before we start

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
            steer(servos, 'forward')
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
                direction      = None
                deadline       = time.time() + ARROW_TIMEOUT
                conflict_count = 0

                while time.time() < deadline:
                    frame     = Camera.capture_frame()
                    direction = detect_arrow(frame)

                    if direction == 'conflict':
                        conflict_count += 1
                        print(f"  Corner/pixel conflict [{conflict_count}/{CONFLICT_MAX_RETRY}] — realigning...")
                        direction = None

                        # Realign laterally without backing up — robot is already
                        # at the right distance; backing up is handled separately
                        # by the "no arrow found" path after CONFLICT_MAX_RETRY.
                        _reposition_to_arrow(servos)

                        if conflict_count >= CONFLICT_MAX_RETRY:
                            break   # give up; fall through to the "no arrow" handler
                        continue

                    if direction in ('left', 'right'):
                        # Only run the physical realignment wiggle if the arrow's
                        # centroid is actually off-centre — a confident direction
                        # reading doesn't imply the robot is poorly aligned.
                        offset = get_arrow_centroid_offset(frame)
                        if offset is not None and abs(offset) <= ALIGN_THRESHOLD_PX:
                            print(f"  Arrow detected: {direction} — already aligned "
                                  f"(offset {offset:+.0f} px), skipping realignment.")
                        else:
                            print(f"  Arrow detected: {direction} — aligning...")
                            # Camera stays running so align_with_arrow() can capture frames.
                            aligned = align_with_arrow(servos)
                            if aligned is not None:
                                direction = aligned
                            print(f"  Final direction after alignment: {direction}")
                        Camera.stop_capture()
                        break

                    # direction is None — wait and try again
                    time.sleep(CAPTURE_INTERVAL)

                if direction is None:
                    # ── Step 5: no arrow found — reverse slightly and retry ────
                    print(f"  No arrow found after {ARROW_TIMEOUT:.0f} s — reversing to retry...")
                    steer(servos, 'forward')
                    move.video_Tracking_Move(BACKUP_SPEED, -1)   # reverse
                    time.sleep(BACKUP_TIME)
                    move.motorStop()
                    continue   # restart the main loop

                # ── Step 4: steer and drive through the junction ─────────────
                print(f"  Turning {direction} and advancing through corner...")
                turn_with_obstacle_check(ultrasonic, servos, direction, TURN_HOLD, TURN_HOLD_OPPOSITE, TURN_SPEED)
                steer(servos, 'forward')

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
        servos.set_angle(STEERING_CANAL, ANGLE_CENTER)
        move.destroy()    # deinitialises the PCA9685 motor driver
        print("Shutdown complete.")


if __name__ == '__main__':
    main()