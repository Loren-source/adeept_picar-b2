#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor


MOTOR_M1_IN1 = 15
MOTOR_M1_IN2 = 14
MOTOR_M2_IN1 = 12
MOTOR_M2_IN2 = 13
MOTOR_M3_IN1 = 11
MOTOR_M3_IN2 = 10
MOTOR_M4_IN1 = 8
MOTOR_M4_IN2 = 9


class RobotMotors:
    def __init__(self):
        i2c = busio.I2C(SCL, SDA)

        self.pwm_motor = PCA9685(i2c, address=0x5f)
        self.pwm_motor.frequency = 50

        self.motor1 = motor.DCMotor(self.pwm_motor.channels[MOTOR_M1_IN1],
                                    self.pwm_motor.channels[MOTOR_M1_IN2])
        self.motor2 = motor.DCMotor(self.pwm_motor.channels[MOTOR_M2_IN1],
                                    self.pwm_motor.channels[MOTOR_M2_IN2])
        self.motor3 = motor.DCMotor(self.pwm_motor.channels[MOTOR_M3_IN1],
                                    self.pwm_motor.channels[MOTOR_M3_IN2])
        self.motor4 = motor.DCMotor(self.pwm_motor.channels[MOTOR_M4_IN1],
                                    self.pwm_motor.channels[MOTOR_M4_IN2])

        self.motors = [self.motor1, self.motor2, self.motor3, self.motor4]

        for m in self.motors:
            m.decay_mode = motor.SLOW_DECAY

    def set_motor(self, channel, direction, speed):
        speed = max(0, min(100, speed))
        throttle = speed / 100

        if direction == -1:
            throttle = -throttle

        self.motors[channel - 1].throttle = throttle

    def set_all_motors(self, direction, speed):
        for i in range(1, 5):
            self.set_motor(i, direction, speed)

    def stop(self):
        for m in self.motors:
            m.throttle = 0

    def forward_slow(self):
        self.set_all_motors(1, 25)

    def backward_slow(self):
        self.set_all_motors(-1, 25)

    def drive_with_ramp(self, speed, direction, ramp_time):
        speed = max(0, min(100, speed))

        steps = 20
        delay = ramp_time / steps

        for current_speed in range(0, speed + 1, max(1, speed // steps)):
            self.set_all_motors(direction, current_speed)
            time.sleep(delay)

    def destroy(self):
        self.stop()
        self.pwm_motor.deinit()


if __name__ == '__main__':
    robot = RobotMotors()

    try:
        while True:
            moteur = input("Quel moteur tester (1-4, q pour quitter) ? ")

            if moteur.lower() == "q":
                break

            moteur = int(moteur)

            sens = input("Sens (A=avant, R=arriere) ? ").upper()

            if sens == "A":
                direction = 1
            else:
                direction = -1

            vitesse = int(input("Vitesse (0-100) ? "))

            robot.set_motor(moteur, direction, vitesse)

            input("Appuie sur Entrée pour arrêter le moteur...")

            robot.set_motor(moteur, 1, 0)

    except KeyboardInterrupt:
        pass

    finally:
        robot.stop()
        robot.destroy()
