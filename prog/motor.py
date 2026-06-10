#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor
from servo import RobotServos


MOTOR_M1_IN1 = 15
MOTOR_M1_IN2 = 14


class RobotMotor:
    def __init__(self):
        i2c = busio.I2C(SCL, SDA)

        self.pwm_motor = PCA9685(i2c, address=0x5f)
        self.pwm_motor.frequency = 50

        self.motor1 = motor.DCMotor(
            self.pwm_motor.channels[MOTOR_M1_IN1],
            self.pwm_motor.channels[MOTOR_M1_IN2]
        )

        self.motor1.decay_mode = motor.SLOW_DECAY

    def set_motor(self, direction, speed):
        speed = max(0, min(100, speed))
        throttle = speed / 100

        if direction == -1:
            throttle = -throttle

        self.motor1.throttle = throttle

    def stop(self):
        self.motor1.throttle = 0

    def forward_slow(self):
        self.set_motor(1, 25)

    def backward_slow(self):
        self.set_motor(-1, 25)

    def drive_with_ramp(self, speed, direction, ramp_time):
        speed = max(0, min(100, speed))

        steps = 20
        delay = ramp_time / steps

        for current_speed in range(0, speed + 1, max(1, speed // steps)):
            self.set_motor(direction, current_speed)
            time.sleep(delay)

    def destroy(self):
        self.stop()
        self.pwm_motor.deinit()


if __name__ == '__main__':
    robot = RobotMotor()
    servos = RobotServos()

    servos.set_angle(0, 88)

    try:
        while True:
            sens = input("Sens (A=avant, R=arriere, S=stop, Q=quitter) ? ").upper()

            if sens == "Q":
                break
            elif sens == "S":
                robot.stop()
                continue
            elif sens == "A":
                direction = 1
            elif sens == "R":
                direction = -1
            else:
                print("Commande inconnue.")
                continue

            vitesse = int(input("Vitesse (0-100) ? "))
            rampe = float(input("Temps de rampe en secondes ? "))

            robot.drive_with_ramp(vitesse, direction, rampe)

    except KeyboardInterrupt:
        pass

    finally:
        robot.destroy()
        servos.pca.deinit()
