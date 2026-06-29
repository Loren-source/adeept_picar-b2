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
from servo import RobotServos         # servo.py  — persistent I2C/PCA9685, no re-init per call
from arrow_detector import detect_arrow   # arrow_detector.py — OpenCV arrow analysis

# ──────────────────────────────────────────────────────────────────────────────
# Tunable constants — adjust these for your maze and robot
# ──────────────────────────────────────────────────────────────────────────────
DIST_MIN         = 35    # cm: stop and read arrow when distance >= DIST_MIN
DIST_MAX         = 40    # cm: stop and read arrow when distance <= DIST_MAX
ARROW_TIMEOUT    = 5.0   # seconds: total time budget for arrow detection attempts
CAPTURE_INTERVAL = 0.5   # seconds: pause between frame captures during detection

# Absolute servo angles for channel 0 (steering) — same scale as tache11.py.
# Centre is slightly above 90 to match the physical servo neutral.
ANGLE_CENTER = 97    # straight ahead
ANGLE_LEFT   = 120   # full left turn
ANGLE_RIGHT  = 65    # full right turn

DRIVE_SPEED  = 30    # throttle % for driving forward  (0–100)
TURN_SPEED   = 60    # throttle % during cornering — needs more torque than straight driving
BACKUP_SPEED = 20    # throttle % for reversing
BACKUP_TIME  = 0.5     # seconds: how long to reverse when no arrow is found
TURN_HOLD    = 1.2   # seconds: hold steering angle while clearing a corner

TURN_OBSTACLE_DIST         = 20   # cm: if obstacle closer than this during a turn, interrupt
TURN_OBSTACLE_BACKUP_TIME  = 0.3  # seconds: how long to reverse after an obstacle mid-turn


# ──────────────────────────────────────────────────────────────────────────────
# Steering helper
# ──────────────────────────────────────────────────────────────────────────────
def steer(servos, direction):
    """
    Set the steering servo (channel 0) to an absolute angle.
    Uses RobotServos which keeps the I2C/PCA9685 connection open persistently,
    avoiding the per-call re-initialisation glitch in RPIservo.ServoCtrl.
    """
    if direction == 'left':
        servos.set_angle(0, ANGLE_LEFT)
    elif direction == 'right':
        servos.set_angle(0, ANGLE_RIGHT)
    else:
        servos.set_angle(0, ANGLE_CENTER)


# ──────────────────────────────────────────────────────────────────────────────
# Turn with mid-turn obstacle check
# ──────────────────────────────────────────────────────────────────────────────
def turn_with_obstacle_check(ultrasonic, servos, direction, duration, speed):
    """
    Steer and drive forward for `duration` seconds while polling the ultrasonic sensor.
    If an obstacle is detected closer than TURN_OBSTACLE_DIST cm the robot:
      1. Stops.
      2. Reverses straight for TURN_OBSTACLE_BACKUP_TIME seconds.
      3. Resumes the turn for however many seconds were still remaining.
    """
    poll_interval = 0.05  # seconds between distance checks

    steer(servos, direction)
    move.video_Tracking_Move(speed, 1)

    remaining = duration
    while remaining > 0:
        t0 = time.time()
        time.sleep(min(poll_interval, remaining))
        remaining -= time.time() - t0

        if remaining <= 0:
            break

        dist = ultrasonic.get_distance() / 10.0  # mm → cm
        if dist < TURN_OBSTACLE_DIST:
            print(f"  Obstacle mid-turn ({dist:.1f} cm) — reversing ({remaining:.2f}s left)...")
            move.motorStop()
            steer(servos, 'forward')
            move.video_Tracking_Move(BACKUP_SPEED, -1)
            time.sleep(TURN_OBSTACLE_BACKUP_TIME)
            move.motorStop()
            print(f"  Resuming turn for {remaining:.2f}s...")
            steer(servos, direction)
            move.video_Tracking_Move(speed, 1)

    move.motorStop()


# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # ── Hardware initialisation ───────────────────────────────────────────────

    # Ultrasonic sensor (GPIO 23 = trigger, 24 = echo — ultra.py defaults)
    ultrasonic = Ultrasonic()

    # RobotServos creates one persistent I2C + PCA9685 connection and caches
    # Servo objects per channel — no re-init glitch on every set_angle call.
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
                    steer(servos, 'forward')
                    move.video_Tracking_Move(BACKUP_SPEED, -1)   # reverse
                    time.sleep(BACKUP_TIME)
                    move.motorStop()
                    continue   # restart the main loop

                # ── Step 4: back up briefly before turning ───────────────────
                # Camera is already stopped — no frames accumulate during this.
                print(f"  Backing up before turn...")
                steer(servos, 'forward')
                move.video_Tracking_Move(BACKUP_SPEED, -1)
                time.sleep(BACKUP_TIME)
                move.motorStop()

                # ── Step 5: steer and drive through the junction ──────────────
                print(f"  Turning {direction} and advancing through corner...")
                time.sleep(0.5)     # let wheels reach their angle before driving
                turn_with_obstacle_check(ultrasonic, servos, direction, TURN_HOLD, TURN_SPEED)
                steer(servos, 'forward')    # straighten up once through

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
        servos.set_angle(0, ANGLE_CENTER)
        move.destroy()    # deinitialises the PCA9685 motor driver
        print("Shutdown complete.")


if __name__ == '__main__':
    main()