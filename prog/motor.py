#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
import Spi_WS2812
import threading
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
        self.led = Spi_WS2812.LED()

    def feux_detresse(self):
        threads = [
            threading.Thread(target=self.led.piloter, args=(2, 'R', 255)),
            threading.Thread(target=self.led.piloter, args=(3, 'R', 255)),
            threading.Thread(target=self.led.piloter, args=(4, 'R', 255)),
            threading.Thread(target=self.led.piloter, args=(5, 'R', 255)),
            threading.Thread(target=self.led.piloter, args=(6, 'R', 255)),
            threading.Thread(target=self.led.piloter, args=(7, 'R', 255)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def stop_feux(self):
        threads = [
            threading.Thread(target=self.led.piloter, args=(2, 'N', 255)),
            threading.Thread(target=self.led.piloter, args=(3, 'N', 255)),
            threading.Thread(target=self.led.piloter, args=(4, 'N', 255)),
            threading.Thread(target=self.led.piloter, args=(5, 'N', 255)),
            threading.Thread(target=self.led.piloter, args=(6, 'N', 255)),
            threading.Thread(target=self.led.piloter, args=(7, 'N', 255)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def set_motor(self, direction, speed):
        speed = max(0, min(100, speed))
        throttle = speed / 100

        if direction == -1:
            throttle = -throttle

        self.motor1.throttle = throttle

    def stop(self):
        self.feux_detresse()
        self.motor1.throttle = 0

    def forward_slow(self):
        self.set_motor(1, 35)

    def backward_slow(self):
        self.set_motor(-1, 35)

    def drive_with_ramp(self, speed, direction, ramp_time):
        self.stop_feux()
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
    servos = RobotServos()                        #corection du probleme d'angle, a retirer si necessaire
    servos.set_angle(0, 98)                       #pareil que ci-dessus

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
