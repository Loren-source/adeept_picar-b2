import time
from motor import RobotMotor
from servo import RobotServos

robot = RobotMotor()
servos = RobotServos()

servos.set_angle(0, 127)

try:
    while True:
        robot.set_motor(1, 30)
        time.sleep(0.05)
except KeyboardInterrupt:
    robot.stopper()
    servos.set_angle(0, 97)
