import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

robot = RobotMotor()
servos = RobotServos()
ultra = Ultrasonic()

servos.set_angle(0, 127)

try:
    while True:
        distance = ultra.get_distance()
        robot.set_motor(1, 30)
        time.sleep(0.05)
except KeyboardInterrupt:
    robot.stopper()
    servos.set_angle(0, 97)
